from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from io import BytesIO
from typing import Any, Callable
from urllib.parse import urlencode
from uuid import UUID

from django.apps import apps
from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.http import FileResponse, Http404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from pypdf import PdfReader

from apps.governance.services.audit_service import AuditService
from apps.system_parameters.services.config_service import ConfigurationService

from ..models import DocumentInstance, DocumentTemplate


class DocumentEngineError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.status_code = status_code


@dataclass(frozen=True)
class DocumentTypeDefinition:
    document_type: str
    source_app_label: str
    source_model: str
    template_code: str
    layout_template_path: str
    permission: str
    context_builder: Callable[[Any, dict[str, Any], DocumentTemplate], dict[str, Any]]
    title: str
    variables_schema: dict[str, Any]


@dataclass(frozen=True)
class CompanyBranding:
    logo_url: str
    company_name: str
    address: str
    phone: str
    email: str
    registration_number: str
    footer_legal_text: str
    accent_colors: dict[str, str]

    @classmethod
    def resolve(cls, reference: str = "COMPANY_BRANDING") -> "CompanyBranding":
        prefix = (reference or "COMPANY_BRANDING").strip().upper()

        def value(suffix: str, default: Any = ""):
            from apps.system_parameters.models import SystemParameter

            candidates = [f"{prefix}_{suffix}", suffix, f"BRANDING_{suffix}"]
            for code in candidates:
                result = ConfigurationService.get_parameter(code, None)
                if result not in (None, ""):
                    return result
                parameter = SystemParameter.objects.filter(code=code, is_active=True).first()
                if parameter is not None and parameter.value_type == "FILE" and parameter.file_value:
                    return parameter.file_value.name
            return default

        logo_value = value("LOGO_FILE", "")
        logo_url = ""
        if logo_value:
            try:
                logo_url = default_storage.url(str(logo_value))
            except Exception:
                logo_url = str(logo_value)
        colors = value("ACCENT_COLORS", {})
        if not isinstance(colors, dict):
            colors = {}
        return cls(
            logo_url=logo_url,
            company_name=str(value("COMPANY_NAME", "Zanzibar Insurance Corporation")),
            address=str(value("ADDRESS", "Bima House, Mlandege Road, Zanzibar City")),
            phone=str(value("PHONE", "+255 659 072 500")),
            email=str(value("EMAIL", "info@zic.co.tz")),
            registration_number=str(value("REGISTRATION_NUMBER", "")),
            footer_legal_text=str(value("FOOTER_LEGAL_TEXT", "This document is system generated.")),
            accent_colors={
                "primary": str(colors.get("primary", "#183a91")),
                "accent": str(colors.get("accent", "#d94754")),
                "table_header": str(colors.get("table_header", "#edf1f4")),
            },
        )

    def as_context(self) -> dict[str, Any]:
        return {
            "logo_url": self.logo_url,
            "company_name": self.company_name,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "registration_number": self.registration_number,
            "footer_legal_text": self.footer_legal_text,
            "accent_colors": self.accent_colors,
        }


class DocumentTypeRegistry:
    _definitions: dict[str, DocumentTypeDefinition] = {}

    @classmethod
    def register(cls, definition: DocumentTypeDefinition):
        normalized = definition.document_type.strip().upper()
        cls._definitions[normalized] = DocumentTypeDefinition(
            **{**definition.__dict__, "document_type": normalized}
        )

    @classmethod
    def get(cls, document_type: str) -> DocumentTypeDefinition:
        definition = cls._definitions.get((document_type or "").strip().upper())
        if definition is None:
            raise DocumentEngineError(
                f"Document type '{document_type}' is not registered.",
                status_code=404,
            )
        return definition

    @classmethod
    def for_instance(cls, instance: DocumentInstance) -> DocumentTypeDefinition:
        definition = cls.get(instance.document_type)
        if (
            definition.source_app_label != instance.source_app_label
            or definition.source_model != instance.source_model
        ):
            raise DocumentEngineError("The document source type is not registered.", status_code=403)
        return definition

    @classmethod
    def choices(cls) -> list[str]:
        return sorted(cls._definitions)

    @classmethod
    def definitions(cls):
        return tuple(cls._definitions.values())


def _quotation_context(source, branding: dict[str, Any], template: DocumentTemplate):
    from types import SimpleNamespace

    from apps.ol_quotations.services.document_service import QuotationDocumentService

    # Reuse the quotation domain context aggregation; the shared engine owns
    # branding, layout, PDF rendering, storage, and history for every module.
    legacy_template = SimpleNamespace(layout_variables={})
    context = QuotationDocumentService.build_context(source, legacy_template)
    context["branding"] = branding
    context["document_title"] = "ORDINARY LIFE QUOTATION"
    context["template_version"] = template.version
    return context


DocumentTypeRegistry.register(
    DocumentTypeDefinition(
        document_type="OL_QUOTATION",
        source_app_label="ol_quotations",
        source_model="olquotation",
        template_code="OL_QUOTATION_UNIFIED",
        layout_template_path="documents/ol_quotation.html",
        permission="ol_quotations.print",
        context_builder=_quotation_context,
        title="Ordinary Life Quotation",
        variables_schema={
            "quote": "object",
            "prospect": "object",
            "plans": "array",
            "riders": "array",
            "benefits": "array",
            "installments": "array",
            "financial": "object",
            "agent": "object",
            "branding": "object",
        },
    )
)


class DocumentEngine:
    TICKET_PURPOSE = "zic.documents.download.v1"
    TICKET_SALT = "zic.documents.download.v1"
    TICKET_MAX_AGE_SECONDS = 300

    @classmethod
    def has_permission(cls, actor, permission_code: str) -> bool:
        if not actor or not getattr(actor, "is_authenticated", False):
            return False
        if getattr(actor, "is_superuser", False):
            return True
        if permission_code == "ol_quotations.print":
            from apps.ol_quotations.permissions import has_quotation_permission

            return has_quotation_permission(actor, "print")
        if hasattr(actor, "has_permission") and actor.has_permission(permission_code):
            return True
        if "." in permission_code and hasattr(actor, "has_module_permission"):
            module, action = permission_code.rsplit(".", 1)
            return actor.has_module_permission(module, action.upper())
        return False

    @classmethod
    def source_model(cls, definition: DocumentTypeDefinition):
        return apps.get_model(definition.source_app_label, definition.source_model)

    @classmethod
    def resolve_source(cls, definition, object_id):
        try:
            return cls.source_model(definition).objects.get(pk=object_id)
        except (ValueError, cls.source_model(definition).DoesNotExist) as exc:
            raise DocumentEngineError("The requested source transaction was not found.", 404) from exc

    @classmethod
    def in_scope(cls, actor, source) -> bool:
        if getattr(actor, "is_superuser", False):
            return True
        partner_id = getattr(source, "partner_id", None)
        if partner_id is None:
            return True
        if hasattr(actor, "can_access_partner"):
            return actor.can_access_partner(partner_id)
        return False

    @classmethod
    def ensure_access(cls, actor, definition, source):
        if not cls.has_permission(actor, definition.permission):
            raise DocumentEngineError(
                f"You do not have permission to render {definition.title} documents.",
                status_code=403,
            )
        if not cls.in_scope(actor, source):
            raise DocumentEngineError("You are not allowed to access this source transaction.", 403)

    @classmethod
    def template_for(cls, definition, as_of=None):
        template = (
            DocumentTemplate.objects.filter(
                code=definition.template_code,
                document_type=definition.document_type,
                is_active=True,
            )
            .order_by("-version")
            .first()
        )
        if template:
            return template
        return DocumentTemplate.objects.create(
            code=definition.template_code,
            name=definition.title,
            document_type=definition.document_type,
            version=1,
            layout_template_path=definition.layout_template_path,
            variables_schema=definition.variables_schema,
            branding_config_reference="COMPANY_BRANDING",
            is_active=True,
        )

    @classmethod
    def _render_pdf(cls, html: str) -> tuple[bytes, int]:
        try:
            from weasyprint import HTML

            pdf = HTML(string=html, base_url=str(settings.BASE_DIR)).write_pdf()
            page_count = len(PdfReader(BytesIO(pdf)).pages)
            return pdf, max(page_count, 1)
        except Exception as exc:
            raise DocumentEngineError(f"Document PDF rendering failed: {exc}", 400) from exc

    @classmethod
    def _correlation_id(cls, request=None) -> str:
        if request is None:
            return ""
        return str(
            request.headers.get("X-Correlation-ID")
            or request.headers.get("X-Request-ID")
            or ""
        )[:100]

    @classmethod
    def render(cls, *, document_type, object_id, actor, request=None) -> DocumentInstance:
        definition = DocumentTypeRegistry.get(document_type)
        source = cls.resolve_source(definition, object_id)
        cls.ensure_access(actor, definition, source)
        template = cls.template_for(definition)
        branding = CompanyBranding.resolve(template.branding_config_reference).as_context()
        context = definition.context_builder(source, branding, template)
        context.update(
            {
                "document_type": definition.document_type,
                "source_type": f"{definition.source_app_label}.{definition.source_model}",
                "source_object_id": str(source.pk),
                "generated_at": timezone.now(),
            }
        )
        try:
            html = render_to_string(template.layout_template_path, context)
        except Exception as exc:
            raise DocumentEngineError(f"Document HTML rendering failed: {exc}", 400) from exc
        pdf, page_count = cls._render_pdf(html)
        digest = hashlib.sha256(pdf).hexdigest()
        stamp = timezone.now().strftime("%Y%m%d%H%M%S%f")
        prefix = f"documents/{definition.document_type.lower()}/{source.pk}/{stamp}-{digest[:12]}"
        preview_reference = default_storage.save(
            f"{prefix}.html",
            ContentFile(html.encode("utf-8"), name=f"{prefix}.html"),
        )
        file_reference = default_storage.save(
            f"{prefix}.pdf",
            ContentFile(pdf, name=f"{prefix}.pdf"),
        )
        instance = DocumentInstance.objects.create(
            document_type=definition.document_type,
            source_app_label=definition.source_app_label,
            source_model=definition.source_model,
            source_object_id=str(source.pk),
            template=template,
            template_version=template.version,
            file_reference=file_reference,
            preview_reference=preview_reference,
            generated_by=actor,
            generated_at=timezone.now(),
            correlation_id=cls._correlation_id(request),
            page_count=page_count,
            checksum=digest,
            mime_type="application/pdf",
            status="GENERATED",
            metadata={
                "source_type": f"{definition.source_app_label}.{definition.source_model}",
                "source_object_id": str(source.pk),
                "template_code": template.code,
                "template_version": template.version,
                "variables": definition.variables_schema,
                "branding_config_reference": template.branding_config_reference,
            },
        )
        AuditService.log_action(
            action="DOCUMENT_GENERATED",
            instance=instance,
            actor=actor,
            request=request,
            after_state={
                "document_id": str(instance.pk),
                "source_type": instance.source_type,
                "source_object_id": instance.source_object_id,
                "template_version": instance.template_version,
                "checksum": instance.checksum,
            },
            reason="Unified document rendered and stored.",
            source_channel="API",
        )
        return instance

    @classmethod
    def _signer(cls):
        return signing.TimestampSigner(key=settings.SECRET_KEY, salt=cls.TICKET_SALT)

    @classmethod
    def issue_download_ticket(cls, instance, actor, request=None) -> tuple[str, datetime]:
        definition = DocumentTypeRegistry.for_instance(instance)
        source = cls.resolve_source(definition, instance.source_object_id)
        cls.ensure_access(actor, definition, source)
        expires_at = timezone.now() + timedelta(seconds=cls.TICKET_MAX_AGE_SECONDS)
        payload = {
            "v": 1,
            "purpose": cls.TICKET_PURPOSE,
            "instance_id": str(instance.pk),
            "source_type": instance.source_type,
            "source_object_id": instance.source_object_id,
            "user_id": str(actor.pk),
            "format": "pdf",
        }
        ticket = cls._signer().sign_object(payload)
        AuditService.log_action(
            action="DOCUMENT_TICKET_ISSUED",
            instance=instance,
            actor=actor,
            request=request,
            after_state={"expires_at": expires_at.isoformat(), "format": "pdf"},
            reason="Short-lived unified document download ticket issued.",
            source_channel="API",
        )
        return ticket, expires_at

    @classmethod
    def validate_ticket(cls, ticket: str, instance: DocumentInstance, request=None):
        if not ticket or len(ticket) > 4096:
            raise DocumentEngineError("The document download ticket is missing or invalid.", 403)
        try:
            payload = cls._signer().unsign_object(ticket, max_age=cls.TICKET_MAX_AGE_SECONDS)
        except signing.SignatureExpired as exc:
            raise DocumentEngineError("The document download ticket has expired. Generate a new link.", 403) from exc
        except signing.BadSignature as exc:
            raise DocumentEngineError("The document download ticket is invalid.", 403) from exc
        if not isinstance(payload, dict) or payload.get("purpose") != cls.TICKET_PURPOSE or payload.get("v") != 1:
            raise DocumentEngineError("The document download ticket is invalid for this resource.", 403)
        if payload.get("format") != "pdf" or str(payload.get("instance_id")) != str(instance.pk):
            raise DocumentEngineError("The document download ticket does not match this document.", 403)
        if payload.get("source_type") != instance.source_type or str(payload.get("source_object_id")) != str(instance.source_object_id):
            raise DocumentEngineError("The document download ticket does not match its source transaction.", 403)
        try:
            UUID(str(payload["user_id"]))
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            raise DocumentEngineError("The document download ticket is invalid.", 403) from exc
        owner = apps.get_model("users", "User").objects.filter(
            pk=payload["user_id"],
            is_active=True,
            status="ACTIVE",
        ).first()
        if owner is None:
            raise DocumentEngineError("The document ticket owner is no longer active.", 403)
        if getattr(request, "user", None) is not None and getattr(request.user, "is_authenticated", False):
            if request.user.pk != owner.pk:
                raise DocumentEngineError("This document ticket belongs to another user.", 403)
        return owner, payload

    @classmethod
    def protected_url(cls, instance, request=None, signed=False, actor=None):
        path = reverse("v1:documents:download", kwargs={"pk": instance.pk})
        if signed:
            ticket, expires_at = cls.issue_download_ticket(instance, actor, request)
            path = f"{path}?{urlencode({'ticket': ticket})}"
            return (request.build_absolute_uri(path) if request is not None else path), expires_at
        return request.build_absolute_uri(path) if request is not None else path

    @classmethod
    def preview_url(cls, instance, request=None):
        path = reverse("v1:documents:preview", kwargs={"pk": instance.pk})
        return request.build_absolute_uri(path) if request is not None else path

    @classmethod
    def stream(cls, *, instance, actor=None, request=None, ticket=None, format_name="pdf"):
        format_name = (format_name or "pdf").strip().lower()
        if format_name not in {"pdf", "html"}:
            raise DocumentEngineError("Unsupported document format.", 400)
        definition = DocumentTypeRegistry.for_instance(instance)
        source = cls.resolve_source(definition, instance.source_object_id)
        via_ticket = bool(ticket)
        if via_ticket:
            ticket_owner, _payload = cls.validate_ticket(ticket, instance, request)
            actor = ticket_owner
            cls.ensure_access(actor, definition, source)
        else:
            if not actor or not getattr(actor, "is_authenticated", False):
                raise DocumentEngineError("Authentication credentials were not provided.", 401)
            cls.ensure_access(actor, definition, source)
        reference = instance.preview_reference if format_name == "html" else instance.file_reference
        if not reference or not default_storage.exists(reference):
            raise Http404("The requested document is no longer available.")
        try:
            handle = default_storage.open(reference, "rb")
        except FileNotFoundError as exc:
            raise Http404("The requested document is no longer available.") from exc
        content_type = "text/html; charset=utf-8" if format_name == "html" else instance.mime_type
        response = FileResponse(handle, content_type=content_type)
        response["Content-Disposition"] = f"inline; filename=document-{instance.pk}.{'html' if format_name == 'html' else 'pdf'}"
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["Pragma"] = "no-cache"
        response["X-Content-Type-Options"] = "nosniff"
        AuditService.log_action(
            action="DOCUMENT_TICKET_DOWNLOADED" if via_ticket else ("DOCUMENT_PREVIEWED" if format_name == "html" else "DOCUMENT_DOWNLOADED"),
            instance=instance,
            actor=actor,
            request=request,
            before_state={"format": format_name},
            after_state={"format": format_name, "source_type": instance.source_type},
            reason="Unified document accessed through a protected stream.",
            source_channel="API",
        )
        return response

    @classmethod
    def payload(cls, instance, request=None, actor=None, signed=True):
        signed_url = None
        expires_at = None
        if signed and actor is not None:
            signed_url, expires_at = cls.protected_url(instance, request, signed=True, actor=actor)
        return {
            "id": str(instance.pk),
            "document_type": instance.document_type,
            "source_type": instance.source_type,
            "source_object_id": instance.source_object_id,
            "source_display": cls.source_display(instance),
            "template_name": instance.template.name,
            "template_code": instance.template.code,
            "template_version": instance.template_version,
            "generated_by_display": cls.user_display(instance.generated_by),
            "generated_at": instance.generated_at.isoformat() if instance.generated_at else None,
            "correlation_id": instance.correlation_id,
            "page_count": instance.page_count,
            "checksum": instance.checksum,
            "mime_type": instance.mime_type,
            "status": instance.status,
            "preview_url": cls.preview_url(instance, request),
            "signed_download_url": signed_url,
            "download_url_expires_at": expires_at.isoformat() if expires_at else None,
        }

    @staticmethod
    def user_display(user):
        if user is None:
            return "System"
        return str(
            getattr(user, "get_full_name", lambda: "")()
            or getattr(user, "full_name", "")
            or getattr(user, "username", "")
            or getattr(user, "email", "")
        )

    @classmethod
    def source_display(cls, instance):
        definition = DocumentTypeRegistry.get(instance.document_type)
        source = cls.resolve_source(definition, instance.source_object_id)
        return str(source)


__all__ = [
    "CompanyBranding",
    "DocumentEngine",
    "DocumentEngineError",
    "DocumentTypeDefinition",
    "DocumentTypeRegistry",
]

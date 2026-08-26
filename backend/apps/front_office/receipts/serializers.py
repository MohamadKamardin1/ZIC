from decimal import Decimal

from rest_framework import serializers

from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptAllocationTargetType,
    ReceiptDocument,
    ReceiptImportBatch,
    ReceiptReversal,
    ReceiptStatusHistory,
)
from apps.front_office.receipts.permissions import has_receipt_permission
from apps.front_office.receipts.services.parameter_resolver import payment_mode_label

_ALLOWED_BY_STATUS = {
    "DRAFT": ["update", "post", "cancel"],
    "POSTED": ["allocate", "reverse"],
    "PARTIALLY_ALLOCATED": ["allocate", "reverse"],
    "FULLY_ALLOCATED": ["reverse"],
    "REVERSED": [],
    "CANCELLED": [],
}

# The entitlement that gates each action (mirrors ReceiptPermission.ACTION_TO_CODE).
_ACTION_PERMISSION = {
    "update": "create",
    "post": "post",
    "cancel": "cancel",
    "allocate": "allocate",
    "reverse": "reverse",
}


def allowed_actions(receipt, user=None):
    """State-aware and permission-aware actions for a receipt.

    Status decides the candidate actions; the requesting user's entitlements
    then prune them. Without a user (or with an unauthenticated actor) the
    status-derived set is returned so non-API consumers keep a stable contract.
    """
    actions = list(_ALLOWED_BY_STATUS.get(receipt.status, []))
    if user is None or not getattr(user, "is_authenticated", False):
        return actions
    if getattr(user, "is_superuser", False):
        return actions
    return [
        action
        for action in actions
        if has_receipt_permission(user, _ACTION_PERMISSION.get(action, action))
    ]


def _actor_name(actor):
    if actor is None:
        return None
    if hasattr(actor, "get_full_name"):
        full = actor.get_full_name() or ""
        if full:
            return full
    return getattr(actor, "username", None) or str(actor)


def _first_premium_proposal(commitment_id):
    """The proposal whose ``first_premium_commitment`` matches a commitment, if any.

    Mirrors the seam's authoritative linkage (OLProposal.first_premium_commitment)
    so allocation options and rows can mark first-premium commitments that, once
    discharged, unlock proposal conversion.
    """
    if not commitment_id:
        return None
    from apps.ol_proposals.models import OLProposal

    return OLProposal.objects.filter(first_premium_commitment_id=commitment_id).first()


def _is_first_premium_commitment(commitment_id):
    return _first_premium_proposal(commitment_id) is not None


def _first_premium_proposal_number(commitment_id):
    proposal = _first_premium_proposal(commitment_id)
    return getattr(proposal, "proposal_number", None) if proposal else None


class ReceiptAllocationSerializer(serializers.ModelSerializer):
    allocated_by = serializers.SerializerMethodField()
    allocated_by_name = serializers.SerializerMethodField()
    commitment = serializers.UUIDField(source="commitment_id", allow_null=True, required=False)
    commitment_number = serializers.SerializerMethodField()
    ol_commitment_allocation = serializers.UUIDField(
        source="ol_commitment_allocation_id", allow_null=True, required=False
    )
    allocation_amount_in_receipt_currency = serializers.SerializerMethodField()
    allocation_amount_in_target_currency = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    source_display = serializers.SerializerMethodField()
    reversed_at = serializers.SerializerMethodField()
    is_first_premium = serializers.SerializerMethodField()
    proposal_number = serializers.SerializerMethodField()
    restored_balance = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptAllocation
        fields = (
            "id",
            "target_type",
            "target_id",
            "target_display",
            "commitment",
            "commitment_number",
            "ol_commitment_allocation",
            "amount",
            "allocation_amount_in_receipt_currency",
            "allocation_amount_in_target_currency",
            "currency",
            "exchange_rate",
            "exchange_rate_used",
            "exchange_rate_source",
            "converted_amount",
            "converted_currency",
            "allocation_status",
            "status",
            "reversal_of",
            "reversed_at",
            "source_display",
            "is_first_premium",
            "proposal_number",
            "restored_balance",
            "narration",
            "allocated_at",
            "allocated_by",
            "allocated_by_name",
            "source_channel",
        )

    def get_allocated_by(self, obj):
        return getattr(obj, "allocated_by_id", None)

    def get_allocated_by_name(self, obj):
        return _actor_name(obj.allocated_by)

    def get_commitment_number(self, obj):
        if obj.commitment_id:
            return obj.commitment.commitment_number
        return obj.target_display or obj.target_id or None

    def get_allocation_amount_in_receipt_currency(self, obj):
        return str(obj.amount)

    def get_allocation_amount_in_target_currency(self, obj):
        return str(obj.converted_amount)

    def get_status(self, obj):
        return obj.allocation_status

    def get_source_display(self, obj):
        return obj.target_display or obj.target_id or None

    def get_reversed_at(self, obj):
        reversal = ReceiptAllocation.objects.filter(reversal_of=obj).order_by("-allocated_at").first()
        return reversal.allocated_at.isoformat() if reversal and reversal.allocated_at else None

    def get_restored_balance(self, obj):
        reversal = ReceiptAllocation.objects.filter(reversal_of=obj).order_by("-allocated_at").first()
        return str(reversal.amount) if reversal and reversal.amount is not None else None

    def get_is_first_premium(self, obj):
        return _is_first_premium_commitment(obj.commitment_id)

    def get_proposal_number(self, obj):
        return _first_premium_proposal_number(obj.commitment_id)


class ReceiptReversalSerializer(serializers.ModelSerializer):
    reversed_by = serializers.SerializerMethodField()
    reversed_by_name = serializers.SerializerMethodField()
    created_by_display = serializers.SerializerMethodField()
    created_at = serializers.SerializerMethodField()
    source_channel = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptReversal
        fields = (
            "id",
            "reversal_number",
            "reason",
            "reversed_allocations",
            "reversed_at",
            "reversed_by",
            "reversed_by_name",
            "created_by_display",
            "created_at",
            "source_channel",
        )

    def get_reversed_by(self, obj):
        return getattr(obj, "reversed_by_id", None)

    def get_reversed_by_name(self, obj):
        return _actor_name(obj.reversed_by)

    def get_created_by_display(self, obj):
        return _actor_name(obj.reversed_by)

    def get_created_at(self, obj):
        return obj.reversed_at.isoformat() if obj.reversed_at else None

    def get_source_channel(self, obj):
        receipt = obj.receipt
        return receipt.source_channel if receipt and receipt.source_channel else None


class ReceiptDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()
    template = serializers.UUIDField(source="template_id", allow_null=True, required=False)
    template_code = serializers.SerializerMethodField()
    template_name = serializers.SerializerMethodField()
    generated_by = serializers.SerializerMethodField()
    generated_by_name = serializers.SerializerMethodField()
    generated_by_display = serializers.SerializerMethodField()
    page_count = serializers.SerializerMethodField()
    urls = serializers.SerializerMethodField()
    preview_url = serializers.SerializerMethodField()
    download_url = serializers.SerializerMethodField()
    signed_download_url = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptDocument
        fields = (
            "id",
            "document_type",
            "document_number",
            "file_reference",
            "html_reference",
            "filename",
            "mime_type",
            "status",
            "template",
            "template_code",
            "template_name",
            "template_version",
            "metadata",
            "generated_by",
            "generated_by_name",
            "generated_by_display",
            "generated_at",
            "uploaded_at",
            "uploaded_by",
            "uploaded_by_name",
            "page_count",
            "urls",
            "preview_url",
            "download_url",
            "signed_download_url",
        )

    def get_uploaded_by(self, obj):
        return getattr(obj, "uploaded_by_id", None)

    def get_uploaded_by_name(self, obj):
        return _actor_name(obj.uploaded_by)

    def get_template_code(self, obj):
        return (obj.metadata or {}).get("template_code") if isinstance(obj.metadata, dict) else None

    def get_template_name(self, obj):
        if obj.template_id and obj.template and obj.template.name:
            return obj.template.name
        metadata = obj.metadata or {}
        if isinstance(metadata, dict) and metadata.get("template_name"):
            return metadata["template_name"]
        code = self.get_template_code(obj)
        return code.replace("_", " ").title() if code else obj.document_type

    def get_generated_by(self, obj):
        return getattr(obj, "generated_by_id", None)

    def get_generated_by_name(self, obj):
        return _actor_name(obj.generated_by)

    def get_generated_by_display(self, obj):
        return _actor_name(obj.generated_by)

    def get_page_count(self, obj):
        if not obj.file_reference:
            return 0
        from django.core.files.storage import default_storage

        if not default_storage.exists(obj.file_reference):
            return 0
        try:
            from pypdf import PdfReader

            with default_storage.open(obj.file_reference, "rb") as handle:
                return len(PdfReader(handle).pages)
        except Exception:
            return 0

    def _document_urls(self, obj):
        from apps.front_office.receipts.services.print_service import ReceiptPrintService

        request = self.context.get("request") if self.context else None
        if request is None:
            return None
        return ReceiptPrintService.document_urls(obj, request) or {}

    def get_urls(self, obj):
        return self._document_urls(obj) or None

    def get_preview_url(self, obj):
        return (self._document_urls(obj) or {}).get("html_url")

    def get_download_url(self, obj):
        return (self._document_urls(obj) or {}).get("pdf_url")

    def get_signed_download_url(self, obj):
        return (self._document_urls(obj) or {}).get("pdf_url")


class ReceiptStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.SerializerMethodField()
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptStatusHistory
        fields = ("id", "from_status", "to_status", "reason", "changed_at", "changed_by", "changed_by_name", "source_channel")

    def get_changed_by(self, obj):
        return getattr(obj, "changed_by_id", None)

    def get_changed_by_name(self, obj):
        return _actor_name(obj.changed_by)


class ReceiptBaseSerializer(serializers.ModelSerializer):
    branch = serializers.UUIDField(source="branch_id", allow_null=True, required=False)
    branch_name = serializers.SerializerMethodField()
    partner = serializers.UUIDField(source="partner_id", allow_null=True, required=False)
    partner_name = serializers.SerializerMethodField()
    payer_name = serializers.SerializerMethodField()
    bank_account = serializers.UUIDField(source="bank_account_id", allow_null=True, required=False)
    bank_account_name = serializers.SerializerMethodField()
    payment_mode_label = serializers.SerializerMethodField()
    posted_by = serializers.SerializerMethodField()
    posted_by_name = serializers.SerializerMethodField()
    reversed_by = serializers.SerializerMethodField()
    reversed_by_name = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()
    branch_display = serializers.SerializerMethodField()
    partner_display = serializers.SerializerMethodField()
    payer_display = serializers.SerializerMethodField()
    payer_id = serializers.SerializerMethodField()
    branch_id = serializers.SerializerMethodField()
    currency_display = serializers.SerializerMethodField()
    payment_mode_display = serializers.SerializerMethodField()
    bank_account_display = serializers.SerializerMethodField()
    bank_account_id = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    source_module_display = serializers.SerializerMethodField()
    source_reference = serializers.SerializerMethodField()
    source_reference_display = serializers.SerializerMethodField()
    created_by_display = serializers.SerializerMethodField()
    posted_by_display = serializers.SerializerMethodField()
    amount_in_words = serializers.SerializerMethodField()
    reversed_reason = serializers.SerializerMethodField()
    cancelled_reason = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = (
            "id",
            "receipt_number",
            "receipt_date",
            "branch",
            "branch_name",
            "branch_display",
            "branch_id",
            "partner",
            "partner_name",
            "partner_display",
            "payer_name",
            "payer_display",
            "payer_id",
            "payer_identity",
            "source_module",
            "source_module_display",
            "source_reference_type",
            "source_reference_id",
            "source_reference",
            "source_reference_display",
            "currency",
            "currency_display",
            "exchange_rate",
            "receipt_amount",
            "allocated_amount",
            "unallocated_amount",
            "payment_mode",
            "payment_mode_label",
            "payment_mode_display",
            "payment_reference",
            "bank_account",
            "bank_account_name",
            "bank_account_display",
            "bank_account_id",
            "narration",
            "status",
            "status_display",
            "posted_at",
            "posted_by",
            "posted_by_name",
            "posted_by_display",
            "reversed_at",
            "reversed_by",
            "reversed_by_name",
            "reversed_reason",
            "cancellation_reason",
            "cancelled_reason",
            "amount_in_words",
            "source_channel",
            "allowed_actions",
            "created_by_display",
            "created_at",
            "updated_at",
        )

    def get_branch_name(self, obj):
        return obj.branch_name_snapshot or (str(obj.branch) if obj.branch_id else None)

    def get_partner_name(self, obj):
        return obj.partner_name_snapshot or (str(obj.partner) if obj.partner_id else None)

    def get_payer_name(self, obj):
        return obj.payer_name

    def get_bank_account_name(self, obj):
        return obj.bank_account_snapshot or (str(obj.bank_account) if obj.bank_account_id else None)

    def get_payment_mode_label(self, obj):
        return payment_mode_label(obj.payment_mode)

    def get_branch_display(self, obj):
        return obj.branch_name_snapshot or (str(obj.branch) if obj.branch_id else None)

    def get_partner_display(self, obj):
        return obj.partner_name_snapshot or (str(obj.partner) if obj.partner_id else None)

    def get_payer_display(self, obj):
        return obj.payer_name or obj.display_partner

    def get_currency_display(self, obj):
        return obj.currency

    def get_payment_mode_display(self, obj):
        return payment_mode_label(obj.payment_mode)

    def get_bank_account_display(self, obj):
        return obj.bank_account_snapshot or (str(obj.bank_account) if obj.bank_account_id else None)

    def get_status_display(self, obj):
        return obj.get_status_display()

    def get_source_module_display(self, obj):
        return obj.get_source_module_display()

    def get_created_by_display(self, obj):
        return _actor_name(obj.created_by)

    def get_posted_by_display(self, obj):
        return _actor_name(obj.posted_by)

    def get_posted_by(self, obj):
        return getattr(obj, "posted_by_id", None)

    def get_posted_by_name(self, obj):
        return _actor_name(obj.posted_by)

    def get_reversed_by(self, obj):
        return getattr(obj, "reversed_by_id", None)

    def get_reversed_by_name(self, obj):
        return _actor_name(obj.reversed_by)

    def get_allowed_actions(self, obj):
        request = self.context.get("request") if self.context else None
        return allowed_actions(obj, getattr(request, "user", None) if request else None)

    def get_payer_id(self, obj):
        return str(obj.partner_id) if obj.partner_id else None

    def get_branch_id(self, obj):
        return str(obj.branch_id) if obj.branch_id else None

    def get_bank_account_id(self, obj):
        return str(obj.bank_account_id) if obj.bank_account_id else None

    def get_source_reference(self, obj):
        return obj.source_reference_id or None

    def get_source_reference_display(self, obj):
        if not obj.source_reference_id:
            return None
        prefix = obj.source_module.replace("_", " ").title() if obj.source_module else ""
        return f"{prefix} {obj.source_reference_id}".strip()

    def get_amount_in_words(self, obj):
        from apps.front_office.receipts.services.amount_in_words import amount_in_words

        return amount_in_words(str(obj.receipt_amount), obj.currency)

    def get_reversed_reason(self, obj):
        reversal = ReceiptReversal.objects.filter(receipt=obj).order_by("-reversed_at").first()
        return reversal.reason if reversal else None

    def get_cancelled_reason(self, obj):
        return obj.cancellation_reason or None


class ReceiptDetailSerializer(ReceiptBaseSerializer):
    allocations = ReceiptAllocationSerializer(many=True, read_only=True)
    reversals = ReceiptReversalSerializer(many=True, read_only=True)
    documents = ReceiptDocumentSerializer(many=True, read_only=True)
    status_history = ReceiptStatusHistorySerializer(many=True, read_only=True)
    audit_timeline = serializers.SerializerMethodField()

    class Meta(ReceiptBaseSerializer.Meta):
        fields = ReceiptBaseSerializer.Meta.fields + (
            "allocations",
            "reversals",
            "documents",
            "status_history",
            "audit_timeline",
        )

    def get_audit_timeline(self, obj):
        from apps.front_office.receipts.services.work_queue import audit_timeline

        return audit_timeline(obj)


class ReceiptDraftSerializer(serializers.ModelSerializer):
    branch = serializers.UUIDField(required=False, allow_null=True)
    partner = serializers.UUIDField(required=False, allow_null=True)
    bank_account = serializers.UUIDField(required=False, allow_null=True)
    # The idempotency key's uniqueness is enforced by create_draft (a duplicate
    # key returns the existing receipt); the model UniqueValidator would reject
    # a legitimate retry before the service's idempotency guard runs.
    idempotency_key = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=64, validators=[]
    )

    class Meta:
        model = Receipt
        fields = (
            "receipt_number",
            "idempotency_key",
            "receipt_date",
            "branch",
            "partner",
            "payer_name",
            "payer_identity",
            "source_module",
            "source_reference_type",
            "source_reference_id",
            "currency",
            "exchange_rate",
            "receipt_amount",
            "payment_mode",
            "payment_reference",
            "bank_account",
            "narration",
        )
        extra_kwargs = {
            "receipt_number": {"required": False, "allow_blank": True},
            "receipt_date": {"required": False},
            "payer_name": {"required": False, "allow_blank": True},
            "currency": {"required": False},
            "exchange_rate": {"required": False},
            "source_module": {"required": False},
        }

    def to_internal_value(self, data):
        internal = super().to_internal_value(data)
        for key in ("branch", "partner", "bank_account"):
            if key in internal:
                internal[f"{key}_id"] = internal.pop(key)
        return internal

    def create(self, validated_data):
        from apps.front_office.receipts.services.receipt_service import create_draft

        actor = self.context.get("request").user if self.context.get("request") else None
        source_channel = self.context.get("source_channel") or "API"
        receipt, created = create_draft(actor=actor, source_channel=source_channel, **validated_data)
        self._created = created
        return receipt

    def update(self, instance, validated_data):
        from apps.front_office.receipts.services.receipt_service import update_draft

        actor = self.context.get("request").user if self.context.get("request") else None
        return update_draft(instance, actor=actor, **validated_data)


class ReceiptReasonSerializer(serializers.Serializer):
    """Mandatory reason for reversal, allocation reversal, and cancellation."""

    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=2000,
        error_messages={
            "required": "A reason is required for this action.",
            "blank": "A reason is required for this action.",
        },
    )


class ReceiptAllocationRequestSerializer(serializers.Serializer):
    """Manual allocation payload: OL_COMMITMENT target, amount, optional rate.

    Cross-currency allocations require a positive ``exchange_rate`` (from the
    receipt currency to the target commitment currency) unless an active rate is
    on file for the pair; ``exchange_rate_source`` records provenance.
    """

    target_type = serializers.ChoiceField(
        choices=[ReceiptAllocationTargetType.OL_COMMITMENT],
        error_messages={"invalid_choice": "Only OL_COMMITMENT allocations are supported."},
    )
    target_id = serializers.CharField(max_length=120, allow_blank=False)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    exchange_rate = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        required=False,
        allow_null=True,
        min_value=Decimal("0.00000001"),
    )
    exchange_rate_source = serializers.CharField(required=False, allow_blank=True, default="")
    narration = serializers.CharField(required=False, allow_blank=True, default="")


class ReceiptImportBatchSerializer(serializers.ModelSerializer):
    """Summary of a bulk import batch; row-level detail is returned separately."""

    created_by = serializers.SerializerMethodField()
    created_by_name = serializers.SerializerMethodField()
    uploaded_by_display = serializers.SerializerMethodField()
    uploaded_at = serializers.SerializerMethodField()
    ok_count = serializers.SerializerMethodField()
    error_count = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptImportBatch
        fields = (
            "id",
            "batch_number",
            "import_mode",
            "status",
            "file_name",
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "committed_rows",
            "failed_rows",
            "ok_count",
            "error_count",
            "summary",
            "created_by",
            "created_by_name",
            "uploaded_by_display",
            "uploaded_at",
            "created_at",
            "updated_at",
        )

    def get_created_by(self, obj):
        return str(obj.created_by_id) if obj.created_by_id else None

    def get_created_by_name(self, obj):
        return obj.created_by.username if obj.created_by_id else None

    def get_uploaded_by_display(self, obj):
        return obj.created_by.username if obj.created_by_id else None

    def get_uploaded_at(self, obj):
        return obj.created_at.isoformat() if obj.created_at else None

    def get_ok_count(self, obj):
        return obj.valid_rows

    def get_error_count(self, obj):
        return obj.invalid_rows


class PartnerPortalReceiptAllocationSerializer(serializers.ModelSerializer):
    """Portal-safe allocation view: no internal audit fields, only the linked
    commitment display plus economic amounts the partner is entitled to see."""

    commitment_number = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptAllocation
        fields = (
            "id",
            "target_type",
            "target_display",
            "commitment_number",
            "amount",
            "converted_amount",
            "converted_currency",
            "allocation_status",
            "allocated_at",
            "narration",
        )

    def get_commitment_number(self, obj):
        if obj.commitment_id:
            return obj.commitment.commitment_number
        return obj.target_display or obj.target_id or None


class PartnerPortalReceiptListSerializer(serializers.ModelSerializer):
    """Read-only partner-scoped receipt: own receipts only, no internal audit.

    Deliberately excludes ``allowed_actions``, ``audit_timeline``,
    ``created_by_display``, and internal identifiers so the portal never leaks
    front-office audit/internal state.
    """

    branch_name = serializers.SerializerMethodField()
    payer_display = serializers.SerializerMethodField()
    payment_mode_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = (
            "id",
            "receipt_number",
            "receipt_date",
            "branch",
            "branch_name",
            "payer_name",
            "payer_display",
            "currency",
            "receipt_amount",
            "allocated_amount",
            "unallocated_amount",
            "payment_mode",
            "payment_mode_display",
            "payment_reference",
            "source_module",
            "source_reference_type",
            "source_reference_id",
            "narration",
            "status",
            "status_display",
            "created_at",
        )

    def get_branch_name(self, obj):
        return obj.branch_name_snapshot or (str(obj.branch) if obj.branch_id else None)

    def get_payer_display(self, obj):
        return obj.payer_name or obj.display_partner

    def get_payment_mode_display(self, obj):
        return payment_mode_label(obj.payment_mode)

    def get_status_display(self, obj):
        return obj.get_status_display()


class PartnerPortalReceiptDetailSerializer(PartnerPortalReceiptListSerializer):
    """Portal detail: own allocations only, still no internal audit leakage."""

    allocations = PartnerPortalReceiptAllocationSerializer(many=True, read_only=True)

    class Meta(PartnerPortalReceiptListSerializer.Meta):
        fields = PartnerPortalReceiptListSerializer.Meta.fields + (
            "exchange_rate",
            "allocations",
            "updated_at",
        )

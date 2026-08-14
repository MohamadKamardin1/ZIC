from collections.abc import Iterable

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.common.models import DomainEvent
from apps.partners.models import Partner, UserPartnerLink
from apps.users.models import User, UserActivityLog


class PartnerLinkServiceError(ValidationError):
    """Raised when a partner-link mutation violates an IAM rule."""


def _request_context(request):
    if request is None:
        return None, ""
    return request.META.get("REMOTE_ADDR"), request.META.get("HTTP_USER_AGENT", "")[:500]


def _can_administer(actor: User) -> bool:
    return bool(
        actor
        and actor.is_authenticated
        and (
            actor.is_superuser
            or actor.has_permission("user_management.administer")
            or actor.has_module_permission("users", "MANAGE")
        )
    )


def _require_admin(actor: User) -> None:
    if not _can_administer(actor):
        raise PartnerLinkServiceError("You are not authorized to administer partner links.")


def _audit(actor, event_type, aggregate, payload, request=None, targets: Iterable[User] = ()):
    ip_address, user_agent = _request_context(request)
    target_list = list(targets)
    if not target_list and actor is not None:
        target_list = [actor]
    for target in target_list:
        UserActivityLog.objects.create(
            user=target,
            action_type=UserActivityLog.ActionType.PERMISSION_CHANGE,
            ip_address=ip_address,
            user_agent=user_agent,
            details={
                "actor_id": str(actor.id) if actor else None,
                "event_type": event_type,
                **payload,
            },
        )
    DomainEvent.objects.create(
        event_type=event_type,
        aggregate_type=aggregate.__class__.__name__,
        aggregate_id=str(aggregate.pk),
        payload={"actor_id": str(actor.id) if actor else None, **payload},
    )


class PartnerLinkService:
    @staticmethod
    def _normalize_ids(values):
        return [str(value) for value in (values or [])]

    @staticmethod
    @transaction.atomic
    def link_user(*, actor, user, partner, data=None, request=None):
        _require_admin(actor)
        data = data or {}
        if not user.is_active:
            raise PartnerLinkServiceError("Inactive users cannot be linked to partners.")
        if not partner.is_available_for_partner_access:
            raise PartnerLinkServiceError("Only active partners can be linked to users.")

        valid_from = data.get("valid_from") or timezone.now()
        valid_to = data.get("valid_to")
        if valid_to and valid_to < valid_from:
            raise PartnerLinkServiceError({"valid_to": "valid_to must be on or after valid_from."})

        existing = UserPartnerLink.objects.filter(user=user, partner=partner, link_status="ACTIVE").first()
        if existing:
            raise PartnerLinkServiceError("This active user-partner link already exists.")

        is_primary = bool(data.get("is_primary", False))
        if is_primary:
            UserPartnerLink.objects.filter(user=user, link_status="ACTIVE", is_primary=True).update(is_primary=False)

        link = UserPartnerLink.objects.create(
            user=user,
            partner=partner,
            link_status="ACTIVE",
            is_primary=is_primary,
            valid_from=valid_from,
            valid_to=valid_to,
            created_by=actor,
        )
        _audit(
            actor,
            "iam.user.partner_linked",
            link,
            {
                "user_id": str(user.id),
                "partner_id": str(partner.id),
                "partner_number": partner.partner_number,
                "is_primary": link.is_primary,
            },
            request,
            [user],
        )
        return link

    @staticmethod
    @transaction.atomic
    def unlink_user(*, actor, link, request=None, reason=""):
        _require_admin(actor)
        if link.link_status == "INACTIVE":
            raise PartnerLinkServiceError("This user-partner link is already inactive.")
        link.link_status = "INACTIVE"
        link.is_primary = False
        link.save(update_fields=["link_status", "is_primary", "updated_at"])
        _audit(
            actor,
            "iam.user.partner_unlinked",
            link,
            {
                "user_id": str(link.user_id),
                "partner_id": str(link.partner_id),
                "partner_number": link.partner.partner_number,
                "reason": (reason or "").strip(),
            },
            request,
            [link.user],
        )
        return link

    @staticmethod
    @transaction.atomic
    def set_primary(*, actor, link, request=None):
        _require_admin(actor)
        if not link.is_current:
            raise PartnerLinkServiceError("Only a current active link can be primary.")
        UserPartnerLink.objects.filter(user=link.user, link_status="ACTIVE", is_primary=True).exclude(pk=link.pk).update(is_primary=False)
        if not link.is_primary:
            link.is_primary = True
            link.save(update_fields=["is_primary", "updated_at"])
        _audit(
            actor,
            "iam.user.primary_partner_changed",
            link,
            {"user_id": str(link.user_id), "partner_id": str(link.partner_id)},
            request,
            [link.user],
        )
        return link

    @staticmethod
    def accessible_partner_queryset(user, queryset):
        """Apply partner scope to a queryset with a `partner` relation."""
        return queryset.filter(partner__in=user.visible_partners())

    @staticmethod
    def get_link_or_raise(link_id):
        try:
            return UserPartnerLink.objects.select_related("user", "partner").get(pk=link_id)
        except UserPartnerLink.DoesNotExist as exc:
            raise PartnerLinkServiceError("User-partner link not found.") from exc

    @staticmethod
    def validate_partner_id(user, partner_id):
        if not user.can_access_partner(partner_id):
            raise PartnerLinkServiceError("You are not authorized to access this partner.")
        return Partner.objects.get(pk=partner_id)

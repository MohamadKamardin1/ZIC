"""Parameter-driven proposal status resolvers.

Proposal lifecycle state is read exclusively from ``ol_parameters.OLProposalStatus``
(``applies_to="PROPOSAL"``). Nothing is hardcoded; an empty catalog is tolerated
for backward compatibility with the quotation handoff until the business seeds it.
"""

from datetime import date

from django.db.models import Q

from apps.ol_parameters.models import OLProposalStatus

PROPOSAL_SCOPE = "PROPOSAL"


def _within_effect(queryset, as_of=None):
    day = as_of or date.today()
    return queryset.filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=day),
        Q(effective_to__isnull=True) | Q(effective_to__gte=day),
    )


def _catalog(as_of=None):
    return _within_effect(OLProposalStatus.objects.filter(is_active=True, applies_to__iexact=PROPOSAL_SCOPE), as_of)


def default_proposal_status(as_of=None):
    """First active PROPOSAL status by display_order then code (seeded DRAFT)."""
    status = _catalog(as_of).order_by("display_order", "code").first()
    return status.code if status else None


def is_valid_proposal_status(code, allow_empty_catalog=False, as_of=None):
    code = (code or "").strip().upper()
    if not code:
        return False
    queryset = _catalog(as_of)
    if not queryset.exists():
        return allow_empty_catalog
    return queryset.filter(code__iexact=code).exists()


def terminal_proposal_statuses(as_of=None):
    return list(_catalog(as_of).filter(is_terminal=True).values_list("code", flat=True))


def allowed_transitions(status_code, as_of=None):
    status = _catalog(as_of).filter(code__iexact=(status_code or "")).order_by("display_order", "code").first()
    if status is None:
        return []
    return list(status.allowed_transitions or [])


def is_expired(proposal, as_of=None):
    day = as_of or date.today()
    return bool(proposal.expiry_date and proposal.expiry_date < day)
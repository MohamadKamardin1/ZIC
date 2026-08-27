from datetime import date
from uuid import UUID

from django.db.models import Q
from django.utils import timezone
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.ol_parameters.models import OLClaimReason, OLClaimType
from apps.ol_policies.models import Policy, PolicyBenefit, PolicyMember, PolicyRider

from .errors import ClaimError, registry_error
from .permissions import HasOLClaimPermission


DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def _effective_queryset(queryset, on_date=None):
    on_date = on_date or timezone.localdate()
    return queryset.filter(is_active=True).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=on_date),
        Q(effective_to__isnull=True) | Q(effective_to__gte=on_date),
    )


def _pagination(request):
    raw_page = request.query_params.get("page", "1")
    raw_size = request.query_params.get("page_size", request.query_params.get("limit", DEFAULT_PAGE_SIZE))
    try:
        page = int(raw_page)
        page_size = int(raw_size)
    except (TypeError, ValueError) as exc:
        raise ClaimError(
            message="Claims option pagination values must be whole numbers.",
            error_code="CLAIM_INVALID_FILTER",
            status_code=400,
            field_errors={"page": ["Use a positive whole-number page."], "page_size": ["Use a whole number from 1 to 100."]},
            resolution_steps=[
                "Set page to 1 or another positive whole number.",
                "Set page_size between 1 and 100, then retry.",
            ],
        ) from exc
    if page < 1 or page_size < 1 or page_size > MAX_PAGE_SIZE:
        raise registry_error(
            "CLAIM_INVALID_FILTER",
            field_errors={"page": ["Page must be at least 1."], "page_size": ["Page size must be between 1 and 100."]},
            resolution_steps=[
                "Set page to 1 or another positive whole-number page.",
                "Set page_size between 1 and 100, then retry.",
            ],
        )
    return page, page_size


def _paged(items, request):
    page, page_size = _pagination(request)
    total = len(items)
    start = (page - 1) * page_size
    end = start + page_size
    return {
        "items": items[start:end],
        "results": items[start:end],
        "count": total,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "has_next": end < total,
            "has_previous": page > 1,
        },
    }


def _q_filter(items, query):
    if not query:
        return items
    needle = query.casefold()
    return [
        item
        for item in items
        if needle in str(item.get("label", "")).casefold()
        or needle in str(item.get("value", "")).casefold()
        or needle in str(item.get("meta", {})).casefold()
    ]


def _option(value, label, **meta):
    return {"value": str(value), "label": label, "meta": meta}


def claim_type_options(query="", on_date=None):
    options = []
    for config in _effective_queryset(OLClaimType.objects.all(), on_date).order_by("claim_category", "name", "code"):
        options.append(
            _option(
                config.code,
                f"{config.code} — {config.name}",
                claim_category=config.claim_category,
                claim_category_display=config.get_claim_category_display(),
                calculation_basis=config.calculation_basis,
                waiting_period_days=config.waiting_period_days or 0,
                require_documents=list(config.require_documents or []),
                require_approval=config.require_approval,
                allow_waiver_of_premium=config.allow_waiver_of_premium,
            )
        )
    return _q_filter(options, query)


def claim_reason_options(query="", claim_type=None, on_date=None):
    queryset = _effective_queryset(OLClaimReason.objects.select_related("claim_type"), on_date)
    if claim_type:
        claim_type_value = str(claim_type).strip()
        try:
            UUID(claim_type_value)
        except (TypeError, ValueError):
            queryset = queryset.filter(claim_type__code__iexact=claim_type_value)
        else:
            queryset = queryset.filter(claim_type__pk=claim_type_value)
    options = [
        _option(
            reason.code,
            f"{reason.code} — {reason.name}",
            reason_category=reason.reason_category,
            reason_category_display=reason.get_reason_category_display(),
            claim_type=reason.claim_type.code if reason.claim_type else None,
            claim_type_display=reason.claim_type.name if reason.claim_type else "All claim types",
        )
        for reason in queryset.order_by("reason_category", "name", "code")
    ]
    return _q_filter(options, query)


def _policy_for_options(policy_id):
    if not policy_id:
        raise registry_error(
            "CLAIM_POLICY_REQUIRED",
            field_errors={"policy_id": ["Select a policy before loading claim benefits or members."]},
        )
    policy = Policy.objects.filter(pk=policy_id).select_related("partner").first()
    if not policy:
        raise registry_error("CLAIM_POLICY_NOT_FOUND", details={"policy_id": str(policy_id)})
    return policy


def benefit_options(policy_id, query=""):
    policy = _policy_for_options(policy_id)
    options = []
    for benefit in PolicyBenefit.objects.filter(policy=policy).order_by("benefit_type", "created_at"):
        options.append(
            _option(
                benefit.pk,
                f"{benefit.benefit_type} — Benefit",
                source="POLICY_BENEFIT",
                benefit_type=benefit.benefit_type,
                amount=str(benefit.amount),
                policy_number=policy.policy_number,
            )
        )
    for rider in PolicyRider.objects.filter(policy=policy).order_by("rider_code", "created_at"):
        options.append(
            _option(
                rider.pk,
                f"{rider.rider_code} — Rider benefit",
                source="POLICY_RIDER",
                benefit_type=rider.rider_code,
                amount=str(rider.amount or rider.sum_assured or 0),
                policy_number=policy.policy_number,
            )
        )
    return _q_filter(options, query)


def member_options(policy_id, query=""):
    policy = _policy_for_options(policy_id)
    options = [
        _option(
            member.pk,
            f"{member.name} — {member.member_relation}",
            member_relation=member.member_relation,
            dob=member.dob.isoformat(),
            gender=member.gender,
            benefit_amount=str(member.benefit_amount),
            policy_number=policy.policy_number,
        )
        for member in PolicyMember.objects.filter(policy=policy, is_active=True).order_by("name", "created_at")
    ]
    return _q_filter(options, query)


class ClaimOptionsBaseView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "view"

    def _response(self, entity, items, request):
        data = _paged(items, request)
        data["entity"] = entity
        return Response(
            {
                "success": True,
                "status_code": 200,
                "message": "OL Claims options retrieved successfully.",
                "data": data,
            }
        )


class ClaimTypeOptionsView(ClaimOptionsBaseView):
    def get(self, request):
        return self._response("types", claim_type_options(request.query_params.get("q", "").strip()), request)


class ClaimReasonOptionsView(ClaimOptionsBaseView):
    def get(self, request):
        return self._response(
            "reasons",
            claim_reason_options(
                request.query_params.get("q", "").strip(),
                request.query_params.get("claim_type") or request.query_params.get("claim_type_id"),
            ),
            request,
        )


class ClaimBenefitOptionsView(ClaimOptionsBaseView):
    def get(self, request):
        return self._response(
            "benefits",
            benefit_options(request.query_params.get("policy_id"), request.query_params.get("q", "").strip()),
            request,
        )


class ClaimMemberOptionsView(ClaimOptionsBaseView):
    def get(self, request):
        return self._response(
            "members",
            member_options(request.query_params.get("policy_id"), request.query_params.get("q", "").strip()),
            request,
        )

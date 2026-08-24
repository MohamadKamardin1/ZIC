"""Health questionnaire serving and answer-trigger evaluation."""

from datetime import date

from django.db import transaction
from django.db.models import Q

from apps.ol_parameters.models import OLHealthQuestionnaire
from apps.ol_proposals import events as proposal_events
from apps.ol_proposals.models import OLProposalHealthAnswer


def applicable_questionnaire(proposal, as_of=None):
    """Return the most specific active effective questionnaire for product/plan."""
    from apps.ol_proposals.services.document_service import proposal_product_and_plan

    product_id, plan_id = proposal_product_and_plan(proposal)
    day = as_of or date.today()
    queryset = OLHealthQuestionnaire.objects.filter(is_active=True).filter(
        Q(effective_from__isnull=True) | Q(effective_from__lte=day),
        Q(effective_to__isnull=True) | Q(effective_to__gte=day),
    )
    candidates = list(queryset)
    scored = []
    for row in candidates:
        scope = row.applies_to_scope
        score = (
            0 if (scope == "PLAN" and row.plan_id == plan_id and plan_id) else
            1 if (scope == "PRODUCT" and row.product_id == product_id and product_id) else
            2 if scope == "GLOBAL" else 3,
        )
        scored.append((score, row))
    scored.sort(key=lambda item: (item[0], item[1].code))
    return scored[0][1] if scored else None


def questionnaire_items(proposal):
    questionnaire = applicable_questionnaire(proposal)
    if questionnaire is None:
        return []
    return list(questionnaire.items.select_related("health_question").order_by("sequence", "code"))


def record_answers(*, proposal, answers, actor=None, source_channel="API", reason=""):
    """Accept answers, evaluate triggers, and move to underwriting when triggered."""
    from apps.ol_proposals.errors import ProposalError

    items = {str(item.health_question_id): item for item in questionnaire_items(proposal)}
    if not items:
        raise ProposalError(
            "No active health questionnaire applies to this proposal's product and plan.",
            error_code="PARAMETER_MISSING",
            status_code=422,
            resolution_steps=[
                "Open OL Parameters > Policy Setup > OL Health Questionnaire.",
                "Configure an active questionnaire for the product/plan (global, product, or plan scope).",
                "Retry once the questionnaire is active and effective.",
            ],
        )

    triggered = False
    answered_count = 0
    with transaction.atomic():
        for answer in answers:
            if not isinstance(answer, dict):
                continue
            question_id = answer.get("health_question")
            item = items.get(str(question_id))
            if item is None:
                continue
            value = answer.get("answer")
            OLProposalHealthAnswer.objects.create(
                proposal=proposal,
                questionnaire_item=item,
                health_question=item.health_question,
                answer=value if isinstance(value, dict) else {"value": value},
                score=item.score,
                triggers_medical=item.trigger_medical_requirement,
            )
            answered_count += 1
            if item.trigger_medical_requirement:
                triggered = True

        if answered_count == 0:
            raise ProposalError(
                "No questionnaire answers could be matched to the applicable health questionnaire.",
                error_code="VALIDATION_ERROR",
                status_code=422,
                resolution_steps=["Confirm the proposal has a plan configuration.", "Retry with the health questions served by this endpoint."],
            )

        if triggered:
            proposal.medical_required = True
            if proposal.status not in ("CANCELLED", "CONVERTED", "EXPIRED"):
                proposal.status = "PENDING_UNDERWRITING"
            proposal.save()
            proposal_events.emit_medical_requirement(
                proposal,
                actor=actor,
                reason=reason or "Health questionnaire triggered a medical requirement.",
                source_channel=source_channel,
            )

    return {"triggered": triggered, "medical_required": proposal.medical_required, "status": proposal.status, "answered": answered_count}
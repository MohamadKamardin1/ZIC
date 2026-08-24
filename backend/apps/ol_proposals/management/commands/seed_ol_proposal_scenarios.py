"""Seed eight demo OL proposal scenarios plus stored failure-proof evidence.

Covers Prompt 12 release scope:
  S1 simple conversion in ENRICHMENT
  S2 employer-linked corporate proposal
  S3 medical-triggered PENDING_UNDERWRITING
  S4 cleared underwriting with loading decision
  S5 PAYMENT_READY awaiting first premium with live commitment
  S6 AWAITING_FIRST_PREMIUM with partial payment
  S7 CONVERTED with issued policy stub
  S8 CANCELLED with reason, plus one EXPIRED via the batch command

Failure proofs (caught and recorded as JSON evidence):
  F1 convert unverified partner            -> PROPOSAL_PARTNER_NOT_VERIFIED
  F2 payment ready with missing documents  -> PROPOSAL_NOT_PAYMENT_READY
  F3 invalid beneficiary shares            -> PROPOSAL_BENEFICIARY_SHARES_INVALID
  F4 convert before first premium posted   -> PROPOSAL_FIRST_PREMIUM_NOT_POSTED
  F5 transition out of a terminal state    -> PROPOSAL_INVALID_TRANSITION
"""

import json
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_commitments.models import OLCommitmentAllocation
from apps.ol_parameters.models import (
    OLCommitmentStatus,
    OLHealthQuestion,
    OLHealthQuestionnaire,
    OLHealthQuestionnaireItem,
)
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposal
from apps.ol_proposals.services import document_service, enrichment_service, health_service
from apps.ol_proposals.services.conversion_service import convert_quotation_to_proposal
from apps.ol_proposals.services.first_premium_service import link_first_premium_commitment
from apps.ol_proposals.services.lifecycle_service import cancel_proposal, transition_proposal
from apps.ol_proposals.services.payment_readiness_service import mark_payment_ready
from apps.ol_proposals.services.policy_conversion_service import convert_proposal_to_policy
from apps.ol_proposals.services.underwriting_service import decide
from apps.ol_quotations.models import (
    OLQuotation,
    OLQuotationPlanConfiguration,
    OLQuotationVersion,
    QuotationStatus,
)
from apps.ordinary_life.models import OLPlan, OLProduct, OLProductVersion
from apps.partners.models import Partner

REPO_DOCS = Path(__file__).resolve().parents[5] / "docs"
PREMIUM = Decimal("50000.00")


def ensure_catalogs():
    call_command("seed_ol_proposal_statuses")
    call_command("seed_ol_proposal_document_requirements")
    call_command("seed_ol_proposal_permissions")
    for code, name, order in (
        ("PENDING", "Pending", 10),
        ("PARTIALLY_PAID", "Partially paid", 20),
        ("COMPLETED", "Completed", 30),
    ):
        OLCommitmentStatus.objects.update_or_create(
            code=code,
            defaults={"name": name, "applies_to": "COMMITMENT", "display_order": order, "is_active": True},
        )


def seed_actor():
    User = get_user_model()
    user, _ = User.objects.get_or_create(
        username="seed_ops",
        defaults={"email": "seed.ops@zic.tz", "is_staff": True, "is_superuser": True},
    )
    return user


def product_plan():
    product, _ = OLProduct.objects.get_or_create(code="OL_ENDOW", defaults={"name": "Endowment"})
    product_version, _ = OLProductVersion.objects.get_or_create(
        product=product,
        version_number=1,
        defaults={"effective_from": date.today() - timedelta(days=30)},
    )
    plan, _ = OLPlan.objects.get_or_create(
        product_version=product_version,
        code="ENDOW-20",
        defaults={
            "name": "Twenty Year Endowment",
            "minimum_sum_assured": Decimal("10000"),
            "maximum_sum_assured": Decimal("1000000"),
        },
    )
    return product_version, plan


def make_partner(number, name, *, corporate=False):
    partner, _ = Partner.objects.get_or_create(
        partner_number=number,
        defaults={
            "partner_type": "CORPORATE" if corporate else "INDIVIDUAL",
            "party_type": "CORPORATE" if corporate else "INDIVIDUAL",
            "first_name": "" if corporate else name.split()[0],
            "surname": "" if corporate else " ".join(name.split()[1:]) or name.split()[0],
            "company_name": name if corporate else "",
            "email": f"{number.lower()}@example.com",
            "is_active": True,
            "status": "ACTIVE",
        },
    )
    return partner


def finalized_quotation(partner, quote_number):
    """ORM construction path (approach 1): build a finalized quotation directly."""
    product_version, plan = product_plan()
    quotation = OLQuotation.objects.create(quote_number=quote_number, currency="TZS")
    quotation.partner = partner
    quotation.partner_verified = True
    quotation.current_version_number = 1
    quotation.status = QuotationStatus.FINALIZED
    quotation.save()
    OLQuotationVersion.objects.create(
        quotation=quotation, version_number=1, status=QuotationStatus.FINALIZED, snapshot={}
    )
    OLQuotationPlanConfiguration.objects.create(
        quotation=quotation,
        product_version=product_version,
        plan=plan,
        base_sum_assured=Decimal("500000.00"),
        term_years=20,
        payment_period_years=20,
        premium_frequency="ANNUAL",
        premium_amount=PREMIUM,
        is_selected=True,
    )
    return quotation


def _quotation(quote_number, partner):
    existing = OLQuotation.objects.filter(quote_number=quote_number).first()
    if existing:
        return existing
    return finalized_quotation(partner, quote_number)


def convert(quote_number, partner):
    """Service path (approach 2): finalize a quotation and run the conversion service."""
    existing = OLProposal.objects.filter(quotation__quote_number=quote_number).first()
    if existing:
        return existing
    quotation = _quotation(quote_number, partner)
    return convert_quotation_to_proposal(
        quotation=quotation,
        actor=seed_actor(),
        source_channel="API",
    ).proposal


def complete_enrichment(proposal):
    actor = seed_actor()
    enrichment_service.apply_section(
        proposal=proposal,
        section="declarations",
        data={"declaration_pep_flag": False, "declaration_aml_flag": False},
        actor=actor,
        suppress_errors=True,
    )
    enrichment_service.apply_section(
        proposal=proposal,
        section="bank_details",
        data={
            "bank_name": "NMB",
            "bank_account_name": f"{proposal.proposal_number} account",
            "bank_account_number": "1234567890",
        },
        actor=actor,
        suppress_errors=True,
    )
    if not proposal.beneficiaries.exists():
        enrichment_service.replace_beneficiaries(
            proposal=proposal,
            items=[{
                "person_name": f"Primary Heir of {proposal.proposal_number}",
                "share_percent": Decimal("100.0000"),
                "is_primary": True,
                "identity_type": "NIN",
                "identity_number": f"SEED-{proposal.proposal_number}",
            }],
            actor=actor,
        )


def upload_mandatory_docs(proposal):
    actor = seed_actor()
    for document_type in ("IDENTITY_DOCUMENT", "SIGNATURE", "KYC_FORM"):
        document_service.upload_document(
            proposal=proposal,
            document_type=document_type,
            file_reference=f"/media/{proposal.proposal_number}/{document_type.lower()}.pdf",
            actor=actor,
        )


def allocate(commitment, amount, reference):
    """Direct ledger path (approach 3): post an allocation against the commitment."""
    OLCommitmentAllocation.objects.create(
        commitment=commitment,
        receipt_reference=reference,
        amount=amount,
        payment_mode="CASH",
        currency=commitment.currency,
        allocated_by=seed_actor(),
    )
    commitment.amount_paid = (Decimal(commitment.amount_paid) or Decimal("0")) + amount
    commitment.status = "COMPLETED" if commitment.amount_paid >= commitment.premium_amount else "PARTIALLY_PAID"
    commitment.save()


def seed_triggering_health():
    question, _ = OLHealthQuestion.objects.get_or_create(
        code="HOSPITALIZED_5Y",
        defaults={
            "name": "Hospitalization history",
            "question_text": "Were you hospitalized in the last five years?",
            "category": "MEDICAL",
            "answer_type": "BOOLEAN",
            "effective_from": date.today() - timedelta(days=30),
            "is_active": True,
        },
    )
    questionnaire, _ = OLHealthQuestionnaire.objects.get_or_create(
        code="OL_GLOBAL_HEALTH",
        defaults={
            "name": "Global health",
            "applies_to_scope": "GLOBAL",
            "version": "1.0",
            "effective_from": date.today() - timedelta(days=30),
            "is_active": True,
        },
    )
    item, _ = OLHealthQuestionnaireItem.objects.get_or_create(
        questionnaire=questionnaire,
        health_question=question,
        defaults={
            "code": "ITEM_HOSPITALIZED_5Y",
            "name": "Hospitalized last 5 years",
            "sequence": 2,
            "mandatory": True,
            "trigger_medical_requirement": True,
            "score": Decimal("25.0000"),
        },
    )
    return question, item


def answer_medical(proposal):
    question, _ = seed_triggering_health()
    return health_service.record_answers(
        proposal=proposal,
        answers=[{"health_question": str(question.pk), "answer": {"value": True}}],
        actor=seed_actor(),
    )


def s1_enrichment_simple():
    proposal = convert("Q-SEED-S1", make_partner("SEED-P01", "Amina Juma"))
    return proposal


def s2_corporate_employer():
    proposal = convert("Q-SEED-S2", make_partner("SEED-P02", "Baraka Mwinyi"))
    employer = make_partner("SEED-EMP01", "Zanzibar Spices Ltd", corporate=True)
    proposal.employer_partner = employer
    proposal.employer_name_snapshot = str(employer)
    proposal.save()
    return proposal


def s3_medical_pending_underwriting():
    proposal = convert("Q-SEED-S3", make_partner("SEED-P03", "Chausiku Khamis"))
    complete_enrichment(proposal)
    answer_medical(proposal)
    proposal.refresh_from_db()
    return proposal


def s4_cleared_with_loading():
    proposal = convert("Q-SEED-S4", make_partner("SEED-P04", "Dotto Saleh"))
    complete_enrichment(proposal)
    answer_medical(proposal)
    decide(
        proposal=proposal,
        decision="load",
        reason="Hospitalization history; +10% premium loading applied.",
        actor=seed_actor(),
        source_channel="API",
    )
    proposal.refresh_from_db()
    return proposal


def s5_payment_ready_live_commitment():
    proposal = convert("Q-SEED-S5", make_partner("SEED-P05", "Essa Maalim"))
    complete_enrichment(proposal)
    upload_mandatory_docs(proposal)
    transition_proposal(
        proposal=proposal,
        to_status="PAYMENT_READY",
        actor=seed_actor(),
        reason="Enrichment and mandatory documents complete.",
        source_channel="API",
    )
    link_first_premium_commitment(proposal=proposal, actor=seed_actor(), source_channel="API")
    proposal.refresh_from_db()
    return proposal


def s6_awaiting_partial_payment():
    proposal = convert("Q-SEED-S6", make_partner("SEED-P06", "Fatma Abeid"))
    complete_enrichment(proposal)
    upload_mandatory_docs(proposal)
    mark_payment_ready(proposal=proposal, actor=seed_actor(), source_channel="API")
    proposal.refresh_from_db()
    allocate(proposal.first_premium_commitment, PREMIUM / 2, f"RCT-SEED-{proposal.proposal_number}-PART1")
    proposal.refresh_from_db()
    return proposal


def s7_converted_with_policy():
    proposal = convert("Q-SEED-S7", make_partner("SEED-P07", "Gharib Jecha"))
    complete_enrichment(proposal)
    upload_mandatory_docs(proposal)
    mark_payment_ready(proposal=proposal, actor=seed_actor(), source_channel="API")
    proposal.refresh_from_db()
    allocate(proposal.first_premium_commitment, PREMIUM, f"RCT-SEED-{proposal.proposal_number}-FULL")
    policy, created = convert_proposal_to_policy(proposal=proposal, actor=seed_actor(), source_channel="API")
    proposal.refresh_from_db()
    return proposal, policy, created


def s8_cancelled_and_expired():
    cancelled = convert("Q-SEED-S8", make_partner("SEED-P08", "Huba Shomari"))
    cancel_proposal(
        proposal=cancelled,
        reason="Customer withdrew the application after comparing products.",
        actor=seed_actor(),
        source_channel="API",
    )

    expiring = convert("Q-SEED-S8E", make_partner("SEED-P09", "Juma Waziri"))
    expiring.expiry_date = date.today() - timedelta(days=2)
    expiring.save(update_fields=["expiry_date"])
    call_command("expire_proposals")
    expiring.refresh_from_db()
    cancelled.refresh_from_db()
    return cancelled, expiring


FAILURE_PROOFS = (
    ("F1", "convert unverified partner", "PROPOSAL_PARTNER_NOT_VERIFIED"),
    ("F2", "mark payment ready with missing documents", "PROPOSAL_NOT_PAYMENT_READY"),
    ("F3", "replace beneficiaries with shares not totalling 100%", "PROPOSAL_BENEFICIARY_SHARES_INVALID"),
    ("F4", "convert to policy before first premium posted", "PROPOSAL_FIRST_PREMIUM_NOT_POSTED"),
    ("F5", "transition a terminal proposal to PAYMENT_READY", "PROPOSAL_INVALID_TRANSITION"),
)


def _proof(exc, scenario_id, action):
    return {
        "scenario_id": scenario_id,
        "action": action,
        "caught": True,
        "http_status": exc.status_code,
        "error_code": exc.error_code,
        "message": exc.message,
        "resolution_steps": list(getattr(exc, "resolution_steps", []) or []),
        "field_errors": getattr(exc, "field_errors", None) or {},
        "details": getattr(exc, "details", None) or {},
    }


def run_failure_proofs(evidence_path):
    """Approach 4: deliberately trigger each guard and store the structured payload."""
    actor = seed_actor()
    results = []

    unverified_quote = _quotation("Q-SEED-F1", make_partner("SEED-PF1", "Khamis Faki"))
    unverified_quote.partner_verified = False
    unverified_quote.save(update_fields=["partner_verified"])
    try:
        convert_quotation_to_proposal(quotation=unverified_quote, actor=actor, source_channel="API")
    except ProposalError as exc:
        results.append(_proof(exc, "F1", FAILURE_PROOFS[0][1]))

    no_docs = convert("Q-SEED-F2", make_partner("SEED-PF2", "Laila Mwamba"))
    try:
        mark_payment_ready(proposal=no_docs, actor=actor, source_channel="API")
    except ProposalError as exc:
        results.append(_proof(exc, "F2", FAILURE_PROOFS[1][1]))

    shares = convert("Q-SEED-F3", make_partner("SEED-PF3", "Mwanajuma Ali"))
    try:
        enrichment_service.replace_beneficiaries(
            proposal=shares,
            items=[{"person_name": "Half Heir", "share_percent": Decimal("50.0000"), "is_primary": True}],
            actor=actor,
        )
    except ProposalError as exc:
        results.append(_proof(exc, "F3", FAILURE_PROOFS[2][1]))

    awaiting = convert("Q-SEED-F4", make_partner("SEED-PF4", "Nuru Bakari"))
    complete_enrichment(awaiting)
    upload_mandatory_docs(awaiting)
    mark_payment_ready(proposal=awaiting, actor=actor, source_channel="API")
    awaiting.refresh_from_db()
    try:
        convert_proposal_to_policy(proposal=awaiting, actor=actor, source_channel="API")
    except ProposalError as exc:
        results.append(_proof(exc, "F4", FAILURE_PROOFS[3][1]))

    terminal = convert("Q-SEED-F5", make_partner("SEED-PF5", "Omari Nyange"))
    if terminal.status not in ("CANCELLED", "CONVERTED", "EXPIRED"):
        cancel_proposal(proposal=terminal, reason="Seeded terminal-state proof.", actor=actor, source_channel="API")
    try:
        transition_proposal(
            proposal=terminal, to_status="PAYMENT_READY", actor=actor, source_channel="API"
        )
    except ProposalError as exc:
        results.append(_proof(exc, "F5", FAILURE_PROOFS[4][1]))

    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "module": "ol_proposals",
        "generated_at": date.today().isoformat(),
        "command": "seed_ol_proposal_scenarios",
        "proofs": results,
    }
    evidence_path.write_text(json.dumps(payload, indent=2, default=str))
    return results


class Command(BaseCommand):
    help = "Seed the eight OL proposal demo scenarios and store failure-proof evidence."

    def add_arguments(self, parser):
        parser.add_argument("--evidence-dir", default=str(REPO_DOCS / "evidence"))

    @transaction.atomic
    def handle(self, *args, **options):
        ensure_catalogs()
        seed_actor()

        summaries = []
        if not OLProposal.objects.filter(quotation__quote_number="Q-SEED-S1").exists():
            p = s1_enrichment_simple()
            summaries.append(("S1", "ENRICHMENT", p.proposal_number))
        if not OLProposal.objects.filter(quotation__quote_number="Q-SEED-S2").exists():
            p = s2_corporate_employer()
            summaries.append(("S2", "ENRICHMENT+EMPLOYER", p.proposal_number))
        if not OLProposal.objects.filter(quotation__quote_number="Q-SEED-S3").exists():
            p = s3_medical_pending_underwriting()
            summaries.append(("S3", "PENDING_UNDERWRITING", p.proposal_number))
        if not OLProposal.objects.filter(quotation__quote_number="Q-SEED-S4").exists():
            p = s4_cleared_with_loading()
            summaries.append(("S4", "CLEARED+LOADING", p.proposal_number))
        if not OLProposal.objects.filter(quotation__quote_number="Q-SEED-S5").exists():
            p = s5_payment_ready_live_commitment()
            summaries.append(("S5", "PAYMENT_READY+COMMITMENT", p.proposal_number))
        if not OLProposal.objects.filter(quotation__quote_number="Q-SEED-S6").exists():
            p = s6_awaiting_partial_payment()
            summaries.append(("S6", "AWAITING_PARTIAL", p.proposal_number))
        s7_done = OLProposal.objects.filter(
            quotation__quote_number="Q-SEED-S7", status="CONVERTED", converted_policy__isnull=False
        ).exists()
        if not s7_done:
            p, policy, created = s7_converted_with_policy()
            summaries.append(("S7", "CONVERTED+POLICY", p.proposal_number))
        if not OLProposal.objects.filter(quotation__quote_number="Q-SEED-S8").exists():
            cancelled, expired = s8_cancelled_and_expired()
            summaries.append(("S8", "CANCELLED", cancelled.proposal_number))
            summaries.append(("S8b", "EXPIRED(batch)", expired.proposal_number))

        evidence_path = Path(options["evidence_dir"]) / "ol_proposals_error_proofs.json"
        proofs = run_failure_proofs(evidence_path)

        self.stdout.write(self.style.SUCCESS(f"Scenarios seeded: {len(summaries)}"))
        for label, note, number in summaries:
            self.stdout.write(f"  {label:<4} {note:<26} {number}")
        self.stdout.write(self.style.SUCCESS(f"Failure proofs captured: {len(proofs)} -> {evidence_path}"))
        for proof in proofs:
            self.stdout.write(f"  {proof['scenario_id']} {proof['error_code']} ({proof['http_status']})")

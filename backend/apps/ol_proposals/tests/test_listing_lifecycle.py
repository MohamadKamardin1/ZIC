from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.common.models import DomainEvent
from apps.governance.models import AuditLog
from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import (
    OLCommitmentStatus,
    OLDefaultParameterValueType,
    OLDefaultSystemParameter,
)
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposal, OLProposalPlanConfig
from apps.ol_proposals.services.lifecycle_service import (
    cancel_proposal,
    reactivate_proposal,
    transition_proposal,
)
from apps.ol_quotations.models import OLQuotation, OLQuotationVersion
from apps.ordinary_life.models import OLPlan, OLProduct, OLProductVersion
from apps.partners.models import Partner

User = get_user_model()


def seed_catalogs():
    call_command("seed_ol_proposal_statuses")
    for code, name, order in (("PENDING", "Pending", 10), ("PARTIALLY_PAID", "Partially paid", 20), ("COMPLETED", "Completed", 30)):
        OLCommitmentStatus.objects.update_or_create(
            code=code, defaults={"name": name, "applies_to": "COMMITMENT", "display_order": order, "is_active": True}
        )


def make_partner(number, name):
    return Partner.objects.create(
        partner_number=number,
        partner_type="INDIVIDUAL",
        party_type="INDIVIDUAL",
        first_name=name.split()[0],
        surname=" ".join(name.split()[1:]),
        email=f"{name.replace(' ', '.').lower()}@example.com",
        is_active=True,
        status="ACTIVE",
    )


def _product_plan():
    product, _ = OLProduct.objects.get_or_create(code="OL_ENDOW", defaults={"name": "Endowment"})
    product_version, _ = OLProductVersion.objects.get_or_create(
        product=product, version_number=1, defaults={"effective_from": date.today() - timedelta(days=30)}
    )
    plan, _ = OLPlan.objects.get_or_create(
        product_version=product_version, code="ENDOW-20",
        defaults={"name": "Twenty Year Endowment", "minimum_sum_assured": Decimal("10000"), "maximum_sum_assured": Decimal("1000000")},
    )
    return product, product_version, plan


def make_proposal(number, status, *, quote_number=None, partner=None, agent=None, employer=None, expiry_offset=30, plan_conf=True, payment_ready=False):
    quotation = OLQuotation.objects.create(quote_number=quote_number or f"Q-{number[-4:]}")
    OLQuotationVersion.objects.create(quotation=quotation, version_number=1, status="FINALIZED")
    proposal = OLProposal(
        quotation=quotation,
        proposal_number=number,
        status=status,
        partner=partner,
        partner_name_snapshot=str(partner) if partner else "",
        agent_partner=agent,
        agent_name_snapshot=str(agent) if agent else "",
        employer_partner=employer,
        employer_name_snapshot=str(employer) if employer else "",
        currency="TZS",
        expiry_date=date.today() + timedelta(days=expiry_offset),
        payment_ready=payment_ready,
        financial_summary_snapshot={"total_premium": "50000.00"},
    )
    proposal.save()
    if plan_conf:
        product, product_version, plan = _product_plan()
        OLProposalPlanConfig.objects.create(
            proposal=proposal, product_version=product_version, plan=plan,
            base_sum_assured=Decimal("500000.00"), term_years=20, payment_period_years=20,
            premium_frequency="ANNUAL", premium_amount=Decimal("50000.00"), is_selected=True,
        )
    return proposal


def link_completed_commitment(proposal):
    commitment = OLCommitment.objects.create(
        commitment_number=f"OLC-{proposal.proposal_number}",
        source_type="PROPOSAL",
        source_object_id=str(proposal.pk),
        source_reference=proposal.proposal_number,
        partner=proposal.partner,
        currency="TZS",
        installment_number=1,
        installment_count=1,
        due_date=date.today(),
        premium_amount=Decimal("50000.00"),
        amount_paid=Decimal("50000.00"),
        status="COMPLETED",
    )
    proposal.first_premium_commitment = commitment
    proposal.save(update_fields=["first_premium_commitment"])
    return commitment


class ListingServiceTests(DRFTestCase):
    def setUp(self):
        seed_catalogs()
        self.superuser = User.objects.create_superuser(username="list_adm", password="Password@12345", email="list_adm@zic.tz")
        self.client.force_authenticate(self.superuser)
        self.policyholder = make_partner("PT-LIST-0001", "Amina Salim")
        self.agent = make_partner("PT-LIST-0002", "Agent Kato")
        self.employer = make_partner("PT-LIST-0003", "Zanzibar Trading Co")
        self.enrich = make_proposal("OLP-2026-L001", "ENRICHMENT", partner=self.policyholder, agent=self.agent, employer=self.employer)
        self.enrich_plain = make_proposal("OLP-2026-L002", "ENRICHMENT", partner=make_partner("PT-LIST-0004", "Juma Mushi"))
        self.posted = make_proposal("OLP-2026-L003", "AWAITING_FIRST_PREMIUM", partner=self.policyholder, payment_ready=True)
        link_completed_commitment(self.posted)

    def test_list_columns_present(self):
        response = self.client.get("/api/v1/ol-proposals/proposals/")
        self.assertEqual(response.status_code, 200)
        rows = response.data["data"]["results"]
        self.assertEqual(len(rows), 3)
        for column in (
            "proposal_number", "policyholder", "agent", "employer", "product", "plan",
            "total_premium", "currency", "status_badge", "payment_ready", "first_premium_posted",
            "expiry_date", "created_at", "allowed_actions",
        ):
            self.assertIn(column, rows[0])

        enrich_row = next(row for row in rows if row["proposal_number"] == "OLP-2026-L001")
        self.assertIn("Amina Salim", enrich_row["policyholder"])
        self.assertIn("Agent Kato", enrich_row["agent"])
        self.assertIn("Zanzibar Trading Co", enrich_row["employer"])
        self.assertEqual(enrich_row["product"], "OL_ENDOW - Endowment")
        self.assertEqual(enrich_row["total_premium"], "50000.00")
        for action in ("view", "enrich", "upload_documents", "mark_payment_ready", "cancel"):
            self.assertIn(action, enrich_row["allowed_actions"])

        posted_row = next(row for row in rows if row["proposal_number"] == "OLP-2026-L003")
        self.assertEqual(posted_row["allowed_actions"], ["view", "cancel"])

    def test_filters_status_employer_search_and_posted(self):
        base = "/api/v1/ol-proposals/proposals/"
        status = self.client.get(base, {"status": "ENRICHMENT"})
        self.assertEqual(status.data["data"]["count"], 2)

        with_employer = self.client.get(base, {"has_employer": "true"})
        self.assertEqual(with_employer.data["data"]["count"], 1)
        self.assertEqual(with_employer.data["data"]["results"][0]["proposal_number"], "OLP-2026-L001")

        search = self.client.get(base, {"search": "Amina"})
        self.assertGreaterEqual(search.data["data"]["count"], 2)

        posted = self.client.get(base, {"first_premium_posted": "true"})
        self.assertEqual([row["proposal_number"] for row in posted.data["data"]["results"]], ["OLP-2026-L003"])

        posted_false = self.client.get(base, {"first_premium_posted": "false"})
        numbers = {row["proposal_number"] for row in posted_false.data["data"]["results"]}
        self.assertNotIn("OLP-2026-L003", numbers)

    def test_kpis(self):
        OLProposal.objects.create(quotation=self.enrich.quotation, proposal_number="OLP-2026-L004", status="PENDING_UNDERWRITING")
        OLProposal.objects.create(quotation=self.enrich_plain.quotation, proposal_number="OLP-2026-L005", status="PAYMENT_READY")
        OLProposal.objects.create(quotation=self.posted.quotation, proposal_number="OLP-2026-L006", status="CONVERTED")
        response = self.client.get("/api/v1/ol-proposals/proposals/kpis/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["total_proposals"], 6)
        self.assertEqual(data["pending_underwriting"], 1)
        self.assertEqual(data["payment_ready"], 1)
        self.assertEqual(data["awaiting_first_premium"], 1)
        self.assertEqual(data["converted"], 1)
        self.assertGreaterEqual(data["converted_in_period"], 1)
        self.assertGreaterEqual(data["expiring_soon"], 1)

    def test_export_csv_respects_filters(self):
        response = self.client.get("/api/v1/ol-proposals/proposals/export/", {"status": "ENRICHMENT"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        body = response.content.decode()
        self.assertTrue(body.startswith("proposal_number,policyholder"))
        lines = [line for line in body.strip().splitlines() if line]
        self.assertEqual(len(lines), 3)  # header + 2 ENRICHMENT rows

    def test_detail_includes_readiness_and_quotation_versions(self):
        response = self.client.get(f"/api/v1/ol-proposals/proposals/{self.posted.pk}/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        for key in ("completeness", "checklist", "quotation_versions", "allowed_actions", "first_premium"):
            self.assertIn(key, data)
        self.assertTrue(data["first_premium"]["first_premium_posted"])
        self.assertEqual(len(data["quotation_versions"]), 1)

    def test_history_timeline_orders_events_with_actor_state_reason(self):
        from apps.ol_proposals import events as proposal_events

        actor = User.objects.create_superuser(username="hist_op", password="Password@12345", email="hist_op@zic.tz")
        proposal_events.emit_created(self.enrich, actor=actor, reason="Created from quotation", source_channel="WEB")
        proposal_events.emit_payment_ready(
            self.enrich, actor=actor, from_status="ENRICHMENT", reason="Checklist passed", source_channel="API"
        )

        response = self.client.get(f"/api/v1/ol-proposals/proposals/{self.enrich.pk}/history/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["proposal_number"], "OLP-2026-L001")

        rows = data["events"]
        self.assertEqual([row["event_type"] for row in rows], ["ProposalCreated", "ProposalPaymentReady"])
        created = rows[0]
        self.assertEqual(created["actor"], "hist_op")
        self.assertEqual(created["to_status"], "ENRICHMENT")
        self.assertEqual(created["source_channel"], "WEB")
        ready = rows[1]
        self.assertEqual(ready["from_status"], "ENRICHMENT")
        self.assertEqual(ready["to_status"], "ENRICHMENT")
        self.assertEqual(ready["reason"], "Checklist passed")


class LifecycleServiceTests(TestCase):
    def setUp(self):
        seed_catalogs()
        self.user = User.objects.create_user(username="life_ops", password="Password@12345", email="life_ops@zic.tz")
        self.proposal = make_proposal("OLP-2026-LC1", "ENRICHMENT", partner=make_partner("PT-LC-0001", "Life Ops Partner"))
        self.admiral = make_proposal("OLP-2026-LC2", "ENRICHMENT", partner=make_partner("PT-LC-0002", "Admiral Partner"))

    def test_cancel_requires_reason_and_audits(self):
        with self.assertRaises(ProposalError) as ctx:
            cancel_proposal(proposal=self.proposal, actor=self.user, reason="", source_channel="API")
        self.assertEqual(ctx.exception.error_code, "VALIDATION_ERROR")

        cancel_proposal(proposal=self.proposal, actor=self.user, reason="Client decided to withdraw", source_channel="API")
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, "CANCELLED")
        self.assertEqual(self.proposal.reason_code, "PROPOSAL_CANCELLED")
        self.assertTrue(AuditLog.objects.filter(action="PROPOSAL_TRANSITION", object_id=str(self.proposal.pk)).exists())
        self.assertEqual(DomainEvent.objects.filter(event_type="ProposalCancelled", aggregate_id=str(self.proposal.pk)).count(), 1)

    def test_invalid_transition_is_teachable(self):
        with self.assertRaises(ProposalError) as ctx:
            transition_proposal(proposal=self.admiral, to_status="CONVERTED", actor=self.user, source_channel="API")
        self.assertEqual(ctx.exception.error_code, "PROPOSAL_INVALID_TRANSITION")
        self.assertTrue(any("Allowed next states" in step for step in ctx.exception.resolution_steps))
        self.assertTrue(any("ENRICHMENT" in step for step in ctx.exception.resolution_steps))

    def test_reactivate_from_expiry_is_parameter_gated(self):
        self.proposal.status = "EXPIRED"
        self.proposal.expiry_date = date.today() - timedelta(days=1)
        self.proposal.save(update_fields=["status", "expiry_date"])

        with self.assertRaises(ProposalError) as ctx:
            reactivate_proposal(proposal=self.proposal, actor=self.user, source_channel="API")
        self.assertEqual(ctx.exception.error_code, "PROPOSAL_INVALID_TRANSITION")

        OLDefaultSystemParameter.objects.create(
            code="PROPOSAL_REACTIVATE_FROM_EXPIRY",
            parameter_key="PROPOSAL_REACTIVATE_FROM_EXPIRY",
            parameter_category="PROPOSAL",
            name="Reactivate expired proposals",
            value_type=OLDefaultParameterValueType.BOOLEAN,
            boolean_value=True,
            effective_from=date.today() - timedelta(days=30),
            is_active=True,
        )
        reactivate_proposal(proposal=self.proposal, actor=self.user, source_channel="API")
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, "ENRICHMENT")


class ExpiryCommandTests(TestCase):
    def setUp(self):
        seed_catalogs()
        self.user = User.objects.create_user(username="exp_ops", password="Password@12345", email="exp_ops@zic.tz")
        self.stale = make_proposal("OLP-2026-EXP1", "ENRICHMENT", partner=make_partner("PT-EXP-0001", "Stale Partner"), expiry_offset=-1)
        self.stale2 = make_proposal("OLP-2026-EXP2", "DRAFT", partner=make_partner("PT-EXP-0002", "Older Partner"), expiry_offset=-5)
        self.future = make_proposal("OLP-2026-EXP3", "ENRICHMENT", partner=make_partner("PT-EXP-0003", "Future Partner"), expiry_offset=30)
        self.already_expired = make_proposal("OLP-2026-EXP4", "EXPIRED", partner=make_partner("PT-EXP-0004", "Dead Partner"), expiry_offset=-10)

    def test_expiry_batch_is_idempotent(self):
        call_command("expire_proposals")
        self.stale.refresh_from_db()
        self.stale2.refresh_from_db()
        self.future.refresh_from_db()
        self.already_expired.refresh_from_db()
        self.assertEqual(self.stale.status, "EXPIRED")
        self.assertEqual(self.stale2.status, "EXPIRED")
        self.assertEqual(self.future.status, "ENRICHMENT")
        self.assertEqual(self.already_expired.status, "EXPIRED")
        self.assertEqual(
            AuditLog.objects.filter(action="PROPOSAL_EXPIRE", source_channel="SYSTEM", object_id__in=[str(self.stale.pk), str(self.stale2.pk)]).count(), 2
        )
        events_before = DomainEvent.objects.filter(event_type="ProposalExpired").count()

        call_command("expire_proposals")
        stale_events = DomainEvent.objects.filter(
            event_type="ProposalExpired", aggregate_id__in=[str(self.stale.pk), str(self.stale2.pk)]
        ).count()
        self.assertEqual(stale_events, 2)
        self.assertEqual(DomainEvent.objects.filter(event_type="ProposalExpired").count(), events_before)


class LifecycleEndpointTests(DRFTestCase):
    def setUp(self):
        seed_catalogs()
        self.superuser = User.objects.create_superuser(username="lc_adm", password="Password@12345", email="lc_adm@zic.tz")
        self.client.force_authenticate(self.superuser)
        self.proposal = make_proposal("OLP-2026-LP1", "ENRICHMENT", partner=make_partner("PT-LP-0001", "Endpoint Partner"))
        self.base = f"/api/v1/ol-proposals/proposals/{self.proposal.pk}"

    def test_cancel_endpoint_requires_reason_and_returns_detail(self):
        missing = self.client.post(f"{self.base}/cancel/", {}, format="json")
        self.assertEqual(missing.status_code, 422)
        self.assertEqual(missing.data["error_code"], "VALIDATION_ERROR")

        ok = self.client.post(f"{self.base}/cancel/", {"reason": "Withdrew application"}, format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data["data"]["status"], "CANCELLED")

    def test_reactivate_endpoint_parameter_gated(self):
        self.proposal.status = "EXPIRED"
        self.proposal.expiry_date = date.today() - timedelta(days=1)
        self.proposal.save(update_fields=["status", "expiry_date"])
        blocked = self.client.post(f"{self.base}/reactivate/", format="json")
        self.assertEqual(blocked.status_code, 422)
        self.assertEqual(blocked.data["error_code"], "PROPOSAL_INVALID_TRANSITION")

        OLDefaultSystemParameter.objects.create(
            code="PROPOSAL_REACTIVATE_FROM_EXPIRY",
            parameter_key="PROPOSAL_REACTIVATE_FROM_EXPIRY",
            parameter_category="PROPOSAL",
            name="Reactivate expired proposals",
            value_type=OLDefaultParameterValueType.BOOLEAN,
            boolean_value=True,
            effective_from=date.today() - timedelta(days=30),
            is_active=True,
        )
        ok = self.client.post(f"{self.base}/reactivate/", format="json")
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(ok.data["data"]["status"], "ENRICHMENT")

    def test_invalid_transition_teachable_via_endpoint(self):
        self.proposal.status = "CONVERTED"
        self.proposal.save(update_fields=["status"])
        response = self.client.post(f"{self.base}/cancel/", {"reason": "Cannot cancel after conversion"}, format="json")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "PROPOSAL_INVALID_TRANSITION")
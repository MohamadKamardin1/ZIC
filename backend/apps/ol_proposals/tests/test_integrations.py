from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APITestCase as DRFTestCase

from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLCommitmentStatus
from apps.ol_proposals.errors import ProposalError
from apps.ol_proposals.models import OLProposal, OLProposalNotificationLog
from apps.ol_proposals.services.audit_consistency import audit_consistency, ensure_audit_consistency
from apps.ol_proposals.services.dashboard_kpi_service import proposal_dashboard_kpis
from apps.ol_proposals.services.lifecycle_service import cancel_proposal, transition_proposal
from apps.ol_proposals.services.notification_service import (
    PROPOSAL_CONVERTED,
    PROPOSAL_EXPIRING_SOON,
    PROPOSAL_PAYMENT_READY,
)
from apps.ol_proposals.services.payment_readiness_service import mark_payment_ready
from apps.ol_quotations.models import OLQuotation, OLQuotationVersion
from apps.partners.models import Partner, UserPartnerLink

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


def make_proposal(number, status, *, partner=None, expiry_offset=30, premium="50000.00", commitment=True):
    quotation = OLQuotation.objects.create(quote_number=f"Q-I-{number[-4:]}")
    quotation.partner = partner
    quotation.partner_verified = True
    quotation.save()
    version = OLQuotationVersion.objects.create(quotation=quotation, version_number=1, status="FINALIZED")
    proposal = OLProposal(
        quotation=quotation,
        quotation_version=version,
        proposal_number=number,
        status=status,
        partner=partner,
        partner_name_snapshot=str(partner) if partner else "",
        currency="TZS",
        expiry_date=date.today() + timedelta(days=expiry_offset),
        payment_ready=status in ("AWAITING_FIRST_PREMIUM", "PAYMENT_READY"),
        financial_summary_snapshot={"total_premium": premium},
    )
    proposal.save()
    if commitment and status == "AWAITING_FIRST_PREMIUM":
        linked = OLCommitment.objects.create(
            commitment_number=f"OLC-{number}",
            source_type="PROPOSAL",
            source_object_id=str(proposal.pk),
            source_reference=proposal.proposal_number,
            partner=partner,
            currency="TZS",
            installment_number=1,
            installment_count=1,
            due_date=date.today(),
            premium_amount=Decimal(premium),
            status="PENDING",
        )
        proposal.first_premium_commitment = linked
        proposal.save(update_fields=["first_premium_commitment"])
    return proposal


def link_user(user, partner):
    UserPartnerLink.objects.create(user=user, partner=partner, link_status="ACTIVE", is_primary=True, valid_from=date.today())


def make_ready_proposal(number, partner):
    from apps.ol_proposals.models import OLProposalBeneficiary
    from apps.ol_proposals.services import document_service

    proposal = make_proposal(number, "ENRICHMENT", partner=partner)
    proposal.declaration_pep_flag = False
    proposal.declaration_aml_flag = False
    proposal.bank_name = "NMB"
    proposal.bank_account_name = "Ready Account"
    proposal.bank_account_number = "1234567890"
    proposal.save(update_fields=["declaration_pep_flag", "declaration_aml_flag", "bank_name", "bank_account_name", "bank_account_number"])
    OLProposalBeneficiary.objects.create(
        proposal=proposal, person_name="Ready Beneficiary", identity_type="NIN",
        identity_number="PR-BEN-0001", share_percent=Decimal("100.0000"), is_primary=True,
    )
    call_command("seed_ol_proposal_document_requirements")
    for document_type in ("IDENTITY_DOCUMENT", "SIGNATURE", "KYC_FORM"):
        document_service.upload_document(
            proposal=proposal, document_type=document_type, file_reference=f"/media/{document_type.lower()}.pdf", actor=None
        )
    return proposal


class DashboardKpiTests(TestCase):
    def setUp(self):
        seed_catalogs()
        self.superuser = User.objects.create_superuser(username="kpi_adm", password="Password@12345", email="kpi_adm@zic.tz")
        self.partner = make_partner("PT-I-0001", "Kpi Partner")
        self.await1 = make_proposal("OLP-2026-I001", "AWAITING_FIRST_PREMIUM", partner=self.partner, premium="10000.00")
        self.await2 = make_proposal("OLP-2026-I002", "AWAITING_FIRST_PREMIUM", partner=self.partner, premium="20000.00")
        self.expiring = make_proposal("OLP-2026-I003", "ENRICHMENT", partner=self.partner, expiry_offset=4)
        self.underwriting = make_proposal("OLP-2026-I004", "PENDING_UNDERWRITING", partner=self.partner, commitment=False)
        self.far = make_proposal("OLP-2026-I005", "ENRICHMENT", partner=self.partner, expiry_offset=30)

    def test_dashboard_kpi_math(self):
        kpis = proposal_dashboard_kpis(user=self.superuser)
        self.assertEqual(kpis["awaiting_first_premium"], 2)
        self.assertEqual(kpis["awaiting_first_premium_amount"], "30000.00")
        self.assertEqual(kpis["expiring_in_7_days"], 1)
        self.assertEqual(kpis["pending_underwriting"], 1)

    def test_dashboard_kpis_role_filtered_to_zero(self):
        viewer = User.objects.create_user(username="kpi_view", password="Password@12345", email="kpi_view@zic.tz")
        kpis = proposal_dashboard_kpis(user=viewer)
        self.assertEqual(kpis, {"awaiting_first_premium": 0, "awaiting_first_premium_amount": "0.00", "expiring_in_7_days": 0, "pending_underwriting": 0})


class NotificationEmissionTests(TestCase):
    def setUp(self):
        seed_catalogs()
        self.user = User.objects.create_user(username="notify_ops", password="Password@12345", email="notify_ops@zic.tz")
        self.partner = make_partner("PT-I-0002", "Notification Partner")
        self.proposal = make_proposal("OLP-2026-I010", "ENRICHMENT", partner=self.partner)

    def test_payment_ready_notification_emitted_once(self):
        ready = make_ready_proposal("OLP-2026-I012", self.partner)
        mark_payment_ready(proposal=ready, actor=self.user, source_channel="API")
        self.assertEqual(
            OLProposalNotificationLog.objects.filter(proposal=ready, event_type=PROPOSAL_PAYMENT_READY).count(), 1
        )
        mark_payment_ready(proposal=ready, actor=self.user, source_channel="API")
        self.assertEqual(
            OLProposalNotificationLog.objects.filter(proposal=ready, event_type=PROPOSAL_PAYMENT_READY).count(), 1
        )

    def test_converted_notification_emitted_once(self):
        self.proposal.status = "AWAITING_FIRST_PREMIUM"
        self.proposal.payment_ready = True
        self.proposal.save(update_fields=["status", "payment_ready"])
        transition_proposal(proposal=self.proposal, to_status="CONVERTED", actor=self.user, source_channel="API")
        self.assertEqual(
            OLProposalNotificationLog.objects.filter(proposal=self.proposal, event_type=PROPOSAL_CONVERTED).count(), 1
        )
        transition_proposal(proposal=self.proposal, to_status="CONVERTED", actor=self.user, source_channel="API")
        self.assertEqual(
            OLProposalNotificationLog.objects.filter(proposal=self.proposal, event_type=PROPOSAL_CONVERTED).count(), 1
        )

    def test_expiring_soon_notification_emitted_once_from_batch(self):
        expiring = make_proposal("OLP-2026-I011", "ENRICHMENT", partner=self.partner, expiry_offset=5)
        call_command("expire_proposals")
        call_command("expire_proposals")
        self.assertEqual(
            OLProposalNotificationLog.objects.filter(proposal=expiring, event_type=PROPOSAL_EXPIRING_SOON).count(), 1
        )


class AuditConsistencyTests(TestCase):
    def setUp(self):
        seed_catalogs()
        self.user = User.objects.create_user(username="audit_ops", password="Password@12345", email="audit_ops@zic.tz")
        self.partner = make_partner("PT-I-0003", "Audit Partner")
        self.proposal = make_proposal("OLP-2026-I020", "ENRICHMENT", partner=self.partner)

    def test_audit_utility_passes_for_recent_proposal(self):
        report = audit_consistency(self.proposal)
        self.assertTrue(report["consistent"], report["problems"])
        self.assertTrue(report["audit_actions"])
        self.assertGreaterEqual(report["audit_count"], 1)

    def test_audit_utility_passes_after_cancel(self):
        cancel_proposal(proposal=self.proposal, actor=self.user, reason="Audit test cancellation")
        self.proposal.refresh_from_db()
        self.assertEqual(self.proposal.status, "CANCELLED")
        report = audit_consistency(self.proposal)
        self.assertTrue(report["consistent"], report["problems"])
        self.assertTrue(ensure_audit_consistency(self.proposal)["consistent"])

    def test_audit_utility_flags_missing_terminal_audit(self):
        self.proposal.status = "EXPIRED"
        self.proposal.save(update_fields=["status"])
        report = audit_consistency(self.proposal)
        self.assertFalse(report["consistent"])
        self.assertTrue(any("EXPIRED" in problem for problem in report["problems"]))
        with self.assertRaises(ProposalError) as ctx:
            ensure_audit_consistency(self.proposal)
        self.assertEqual(ctx.exception.error_code, "PROPOSAL_AUDIT_INCONSISTENT")


class ReportingRegistrationTests(TestCase):
    def test_category_and_dataset_registered(self):
        call_command("seed_ol_proposal_reporting")
        from apps.ol_parameters.models import OLParameterTableRegistry
        from apps.users.models import ReportCategory

        category = ReportCategory.objects.get(code="OL_PROPOSALS")
        self.assertEqual(category.name, "Ordinary Life Proposals")
        self.assertTrue(category.is_active)

        registry = OLParameterTableRegistry.objects.get(slug="ol-proposals-report")
        for field in ("status", "product", "agent", "total_premium", "expiry_date", "created_at"):
            self.assertIn(field, registry.visible_columns)
        self.assertEqual(registry.parameter_group, "REPORT")
        self.assertEqual(registry.model_label, "ol_proposals.OLProposal")


class PartnerPortalTests(DRFTestCase):
    def setUp(self):
        seed_catalogs()
        self.partner_a = make_partner("PT-I-0004", "Alpha Client")
        self.partner_b = make_partner("PT-I-0005", "Beta Client")
        self.proposal_a = make_proposal("OLP-2026-I030", "ENRICHMENT", partner=self.partner_a)
        self.proposal_b = make_proposal("OLP-2026-I031", "ENRICHMENT", partner=self.partner_b)
        self.user_a = User.objects.create_user(username="alpha_user", password="Password@12345", email="alpha@example.com")
        self.user_b = User.objects.create_user(username="beta_user", password="Password@12345", email="beta@example.com")
        self.user_none = User.objects.create_user(username="none_user", password="Password@12345", email="none@example.com")
        link_user(self.user_a, self.partner_a)
        link_user(self.user_b, self.partner_b)

    def test_portal_list_scoped_to_linked_partner(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.get("/api/v1/ol-proposals/proposals/portal/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 1)
        self.assertEqual(response.data["data"]["results"][0]["proposal_number"], "OLP-2026-I030")

    def test_portal_detail_denies_other_partner_with_sanitized_error(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.get(f"/api/v1/ol-proposals/proposals/portal/{self.proposal_b.pk}/")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error_code"], "PROPOSAL_NOT_FOUND")
        payload = response.json()["error"]
        self.assertNotIn(self.proposal_b.proposal_number, str(payload))
        self.assertNotIn("Beta Client", str(payload))

    def test_portal_user_without_partner_gets_empty_list(self):
        self.client.force_authenticate(self.user_none)
        response = self.client.get("/api/v1/ol-proposals/proposals/portal/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["data"]["count"], 0)

    def test_portal_detail_contains_no_internal_actions(self):
        self.client.force_authenticate(self.user_a)
        response = self.client.get(f"/api/v1/ol-proposals/proposals/portal/{self.proposal_a.pk}/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertNotIn("allowed_actions", data)
        self.assertNotIn("enrich", data)
        self.assertEqual(data["proposal_number"], "OLP-2026-I030")

    def test_portal_detail_exposes_read_only_documents(self):
        from apps.ol_proposals.models import OLProposalDocument

        OLProposalDocument.objects.create(
            proposal=self.proposal_a,
            document_type="NATIONAL_ID",
            file_reference="DMS-77",
            mandatory=True,
            status="APPROVED",
        )
        self.client.force_authenticate(self.user_a)
        response = self.client.get(f"/api/v1/ol-proposals/proposals/portal/{self.proposal_a.pk}/")
        self.assertEqual(response.status_code, 200)
        documents = response.data["data"]["documents"]
        self.assertEqual(len(documents), 1)
        self.assertEqual(documents[0]["document_type"], "NATIONAL_ID")
        self.assertNotIn("allowed_actions", response.data["data"])

    def test_notifications_feed_lists_events_with_deep_links(self):
        from apps.ol_proposals.services.notification_service import notify_converted, notify_payment_ready

        notify_payment_ready(proposal=self.proposal_a)
        notify_converted(proposal=self.proposal_a)

        staff = User.objects.create_user(
            username="feed_staff", password="Password@12345", email="feed_staff@example.com", is_superuser=True
        )
        self.client.force_authenticate(staff)
        response = self.client.get("/api/v1/ol-proposals/proposals/notifications/")
        self.assertEqual(response.status_code, 200)
        results = response.data["data"]["results"]
        self.assertGreaterEqual(len(results), 2)
        titles = " | ".join(item["title"] for item in results)
        self.assertIn("OLP-2026-I030 is payment ready", titles)
        self.assertIn("OLP-2026-I030 converted to policy", titles)
        for item in results:
            self.assertEqual(item["deep_link"], f"/ordinary-life/proposals/{self.proposal_a.pk}")
            self.assertNotIn(str(self.proposal_a.pk), item["message"])

    def test_notifications_feed_requires_view_permission(self):
        self.client.force_authenticate(self.user_none)
        response = self.client.get("/api/v1/ol-proposals/proposals/notifications/")
        self.assertEqual(response.status_code, 403)
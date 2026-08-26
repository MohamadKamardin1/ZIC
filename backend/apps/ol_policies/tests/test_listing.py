from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from apps.ol_commitments.models import OLCommitment
from apps.ol_policies.models import Policy, PolicyStatus
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class PolicyListingAndKPITest(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="listing-admin",
            email="listing-admin@example.com",
            password="Strong-listing-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-LIST-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Fatma Said",
            email="fatma.list@example.com",
            mobile_number="+255711200001",
            phone="+255711200001",
            identification_number="NIDA-LIST-1",
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-LIST-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Hassan Broker",
            email="hassan.list@example.com",
            mobile_number="+255711200002",
            phone="+255711200002",
        )
        self.client.force_authenticate(self.user)

    def make_policy(self, *, suffix, status, commencement, maturity, sum_assured, plan_ref):
        quotation = OLQuotation.objects.create(
            quote_number=f"QT-LIST-{suffix}",
            quote_name=f"Listing quote {suffix}",
            quote_date=commencement,
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number=f"PROP-LIST-{suffix}",
            status="CONVERTED",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        return Policy.objects.create(
            proposal_ref=proposal,
            partner=self.partner,
            agent=self.agent,
            product_plan_ref=plan_ref,
            currency="TZS",
            sum_assured=sum_assured,
            premium_amount=Decimal("120000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=commencement,
            maturity_date=maturity,
            status=status,
            contract_snapshot={
                "plans": [{"product_code": "ZIC_OL", "plan_name": plan_ref}],
                "installments": [{"number": 1, "amount": "120000.00"}],
            },
        )

    def test_list_has_table_columns_search_filters_pagination_and_sorting(self):
        today = date.today()
        active = self.make_policy(
            suffix="0001",
            status=PolicyStatus.ACTIVE,
            commencement=today,
            maturity=today + timedelta(days=20),
            sum_assured=Decimal("1000000.00"),
            plan_ref="OL_TERM_STANDARD",
        )
        self.make_policy(
            suffix="0002",
            status=PolicyStatus.LAPSED,
            commencement=today - timedelta(days=400),
            maturity=today + timedelta(days=400),
            sum_assured=Decimal("2000000.00"),
            plan_ref="OL_TERM_FAMILY",
        )

        response = self.client.get(
            "/api/v1/ol/policies/",
            {"search": "NIDA-LIST-1", "status": "ACTIVE", "page": 1, "page_size": 1, "ordering": "policy_number"},
        )
        self.assertEqual(response.status_code, 200)
        payload = response.data["data"]
        self.assertEqual(payload["count"], 1)
        self.assertEqual(payload["page_size"], 1)
        row = payload["results"][0]
        self.assertEqual(row["policy_number"], active.policy_number)
        for field in (
            "policyholder_name",
            "product_name",
            "plan_name",
            "sum_assured",
            "premium_amount",
            "status_display",
            "risk_commencement_date",
            "maturity_date",
            "agent_name",
            "allowed_actions",
        ):
            self.assertIn(field, row)
        self.assertIn("view", row["allowed_actions"])
        self.assertIn("service", row["allowed_actions"])

    def test_kpis_calculate_active_lapsed_new_and_maturing_values(self):
        today = date.today()
        self.make_policy(
            suffix="0010",
            status=PolicyStatus.ACTIVE,
            commencement=today,
            maturity=today + timedelta(days=10),
            sum_assured=Decimal("1000000.00"),
            plan_ref="OL_PLAN_A",
        )
        self.make_policy(
            suffix="0011",
            status=PolicyStatus.ACTIVE,
            commencement=today - timedelta(days=50),
            maturity=today + timedelta(days=45),
            sum_assured=Decimal("3000000.00"),
            plan_ref="OL_PLAN_B",
        )
        self.make_policy(
            suffix="0012",
            status=PolicyStatus.LAPSED,
            commencement=today - timedelta(days=500),
            maturity=today + timedelta(days=90),
            sum_assured=Decimal("4000000.00"),
            plan_ref="OL_PLAN_C",
        )

        response = self.client.get("/api/v1/ol/policies/kpis/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["total_active_policies"], 2)
        self.assertEqual(data["total_sum_assured"], "4000000.00")
        self.assertEqual(data["new_policies_this_month"], 1)
        self.assertEqual(data["lapsed_policies_count"], 1)
        self.assertEqual(data["lapsed_policies_value"], "4000000.00")
        self.assertEqual(data["maturing_soon_count"], 1)
        self.assertEqual(data["currency"], "TZS")
        self.assertEqual(data["sum_assured_by_currency"], {"TZS": "4000000.00"})
        self.assertTrue(data["timestamp"])

    def test_detail_includes_snapshot_children_installments_commitments_and_proposal(self):
        today = date.today()
        policy = self.make_policy(
            suffix="0020",
            status=PolicyStatus.ACTIVE,
            commencement=today,
            maturity=today + timedelta(days=365),
            sum_assured=Decimal("5000000.00"),
            plan_ref="OL_PLAN_DETAIL",
        )
        OLCommitment.objects.create(
            commitment_number="COM-POLICY-DETAIL-1",
            source_type="POLICY",
            source_reference=policy.policy_number,
            partner=self.partner,
            currency="TZS",
            premium_frequency="ANNUALLY",
            due_date=today + timedelta(days=30),
            premium_amount=Decimal("120000.00"),
            balance=Decimal("120000.00"),
            status="PENDING",
        )

        response = self.client.get(f"/api/v1/ol/policies/{policy.pk}/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["linked_proposal"]["proposal_number"], "PROP-LIST-0020")
        self.assertEqual(data["installments"][0]["number"], 1)
        self.assertEqual(data["linked_commitments"][0]["commitment_number"], "COM-POLICY-DETAIL-1")
        self.assertEqual(data["linked_commitments"][0]["status"], "PENDING")
        self.assertIn("audit_logs", data)

    def test_csv_export_respects_filters_and_uses_display_names(self):
        today = date.today()
        policy = self.make_policy(
            suffix="0030",
            status=PolicyStatus.ACTIVE,
            commencement=today,
            maturity=today + timedelta(days=365),
            sum_assured=Decimal("7000000.00"),
            plan_ref="OL_EXPORT_PLAN",
        )
        self.make_policy(
            suffix="0031",
            status=PolicyStatus.LAPSED,
            commencement=today - timedelta(days=500),
            maturity=today + timedelta(days=200),
            sum_assured=Decimal("9000000.00"),
            plan_ref="OL_OTHER_PLAN",
        )

        response = self.client.get("/api/v1/ol/policies/export/", {"status": "ACTIVE"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        content = response.content.decode()
        self.assertIn("Policy Number,Policyholder,Product / Plan", content)
        self.assertIn(policy.policy_number, content)
        self.assertIn("ZIC-LIST-P-0001 — Fatma Said", content)
        self.assertIn("OL_EXPORT_PLAN", content)
        self.assertNotIn("OL_OTHER_PLAN", content)

from datetime import date, timedelta
from decimal import Decimal
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from apps.ol_maturity_installments.models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partner_onboarding.models import Branch, Location
from apps.partners.models import Partner, PartnerBankAccount

LIST_URL = "/api/v1/ol/maturity-installments/"
KPIS_URL = "/api/v1/ol/maturity-installments/kpis/"
EXPORT_URL = "/api/v1/ol/maturity-installments/export/"
DETAIL_URL = "/api/v1/ol/maturity-installments/{plan_id}/"
PROCESS_URL = "/api/v1/ol/maturity-installments/items/{item_id}/process-payment/"
CONFIRM_URL = "/api/v1/ol/maturity-installments/items/{item_id}/confirm-payment/"


class InstallmentListKpiExportTestCase(APITestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_superuser(
            username="installments-list",
            email="installments-list@example.com",
            password="Strong-list-password-123!",
        )
        self.partner = Partner.objects.create(
            partner_number="ZIC-MIP-L-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="List Policyholder One",
            email="list.one@example.com",
            mobile_number="+255711800001",
            phone="+255711800001",
        )
        PartnerBankAccount.objects.create(
            partner=self.partner,
            bank_name="CRDB Bank",
            branch_name="Dar es Salaam",
            account_name="List Policyholder One",
            account_number="2222222222",
            swift_code="CORUTZTZ",
            iban="TZ0022222222222",
            currency="TZS",
            is_primary=True,
            is_verified=True,
        )
        self.agent = Partner.objects.create(
            partner_number="ZIC-MIP-L-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="List Agent",
            email="list.agent@example.com",
            mobile_number="+255711800002",
            phone="+255711800002",
        )
        self.policy = self._policy("POL-MIP-LIST-0001", "QT-MIP-LIST-0001", "PROP-MIP-LIST-0001")
        self.client.force_authenticate(self.user)

    def _policy(
        self,
        policy_number,
        quote_number,
        proposal_number,
        product="OL_ENDOWMENT_STANDARD",
        location_master=None,
        partner=None,
    ):
        partner = partner or self.partner
        quotation = OLQuotation.objects.create(
            quote_number=quote_number,
            quote_name="List KPI quote",
            quote_date=date(2026, 1, 1),
            partner=partner,
            currency="TZS",
            location=location_master.name if location_master else "",
            location_master=location_master,
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number=proposal_number,
            status="POLICY_ISSUED",
            partner=partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        return Policy.objects.create(
            policy_number=policy_number,
            proposal_ref=proposal,
            partner=partner,
            agent=self.agent,
            product_plan_ref=product,
            currency="TZS",
            sum_assured=Decimal("25000000.00"),
            premium_amount=Decimal("125000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2016, 1, 15),
            maturity_date=date(2026, 1, 14),
            status="MATURED",
        )

    def _plan(
        self,
        policy=None,
        *,
        total=Decimal("2000000.00"),
        count=2,
        status=InstallmentPlanStatus.CREATED,
        start_date=date(2025, 1, 14),
        end_date=date(2026, 1, 14),
        partner=None,
    ):
        return OLMaturityInstallmentPlan.objects.create(
            policy_ref=policy or self.policy,
            partner=partner or self.partner,
            currency="TZS",
            total_maturity_value=total,
            total_payable_amount=total,
            installment_count=count,
            frequency="ANNUAL",
            start_date=start_date,
            end_date=end_date,
            status=status,
            created_by=self.user,
        )

    def _item(self, plan, number, due_date, amount, status=InstallmentItemStatus.SCHEDULED):
        return OLInstallmentItem.objects.create(
            plan_ref=plan,
            installment_number=number,
            due_date=due_date,
            amount=amount,
            status=status,
            created_by=self.user,
        )

    def _pay(self, item):
        self.client.post(PROCESS_URL.format(item_id=item.pk))
        response = self.client.post(CONFIRM_URL.format(item_id=item.pk))
        self.assertEqual(response.status_code, 200)

    # ------------------------------------------------------------------
    # List columns and display names
    # ------------------------------------------------------------------

    def test_list_returns_required_columns_and_display_names(self):
        plan = self._plan(status=InstallmentPlanStatus.ACTIVE)
        self._item(plan, 1, date(2025, 1, 14), Decimal("1000000.00"))
        self._item(plan, 2, date(2026, 1, 14), Decimal("1000000.00"))
        response = self.client.get(LIST_URL)
        self.assertEqual(response.status_code, 200, response.data)
        row = response.data["data"]["results"][0]
        for key in (
            "plan_number",
            "policy_number",
            "policyholder_name",
            "total_amount",
            "paid_amount",
            "balance",
            "status",
            "start_date",
            "allowed_actions",
        ):
            self.assertIn(key, row)
        self.assertEqual(row["plan_number"], plan.plan_number)
        self.assertEqual(row["policy_number"], self.policy.policy_number)
        self.assertEqual(row["policyholder_name"], "List Policyholder One")
        self.assertEqual(row["total_amount"], "2000000.00")
        self.assertEqual(row["paid_amount"], "0.00")
        self.assertEqual(row["balance"], "2000000.00")
        self.assertEqual(row["status"], "ACTIVE")
        self.assertEqual(row["status_display"], "Active")
        self.assertIn("view", row["allowed_actions"])
        self.assertNotIn(str(self.partner.pk), row["policyholder_name"])

    def test_list_columns_reflect_paid_and_balance(self):
        plan = self._plan(status=InstallmentPlanStatus.ACTIVE)
        item = self._item(plan, 1, date(2025, 1, 14), Decimal("1000000.00"))
        self._pay(item)
        row = self.client.get(LIST_URL).data["data"]["results"][0]
        self.assertEqual(row["paid_amount"], "1000000.00")
        self.assertEqual(row["balance"], "1000000.00")

    # ------------------------------------------------------------------
    # Filters and search
    # ------------------------------------------------------------------

    def test_list_filters_by_status_and_product(self):
        term_policy = self._policy("POL-MIP-PROD-0002", "QT-MIP-PROD-0002", "PROP-MIP-PROD-0002", product="OL_TERM_PROTECT")
        self._plan(status=InstallmentPlanStatus.ACTIVE)
        self._plan(policy=term_policy, status=InstallmentPlanStatus.COMPLETED)

        active = self.client.get(LIST_URL + "?status=ACTIVE").data["data"]
        self.assertEqual(active["count"], 1)

        term = self.client.get(LIST_URL + "?product=TERM").data["data"]
        self.assertEqual(term["count"], 1)
        self.assertEqual(term["results"][0]["policy_number"], "POL-MIP-PROD-0002")

    def test_list_filters_by_branch(self):
        branch_a = Branch.objects.create(code="DAR-BR", name="Dar es Salaam Branch", is_active=True)
        loc_a = Location.objects.create(branch=branch_a, code="DAR-LOC", name="Dar es Salaam", is_active=True)
        policy_a = self._policy("POL-MIP-BRANCH-0001", "QT-MIP-BRANCH-0001", "PROP-MIP-BRANCH-0001", location_master=loc_a)
        plan_a = self._plan(policy=policy_a, status=InstallmentPlanStatus.ACTIVE)

        branch_b = Branch.objects.create(code="ZNZ-BR", name="Zanzibar Branch", is_active=True)
        loc_b = Location.objects.create(branch=branch_b, code="ZNZ-LOC", name="Zanzibar", is_active=True)
        policy_b = self._policy("POL-MIP-BRANCH-0002", "QT-MIP-BRANCH-0002", "PROP-MIP-BRANCH-0002", location_master=loc_b)
        self._plan(policy=policy_b, status=InstallmentPlanStatus.ACTIVE)
        self._plan(status=InstallmentPlanStatus.ACTIVE)

        by_code = self.client.get(LIST_URL + "?branch=DAR-BR").data["data"]
        self.assertEqual(by_code["count"], 1)
        self.assertEqual(by_code["results"][0]["plan_number"], plan_a.plan_number)

        by_name = self.client.get(LIST_URL + "?branch=Zanzibar%20Branch").data["data"]
        self.assertEqual(by_name["count"], 1)
        self.assertEqual(by_name["results"][0]["policy_number"], "POL-MIP-BRANCH-0002")

    def test_list_filters_by_date_range(self):
        self._plan(status=InstallmentPlanStatus.ACTIVE, start_date=date(2024, 6, 1), end_date=date(2025, 6, 1))
        late = self._plan(status=InstallmentPlanStatus.ACTIVE, start_date=date(2026, 6, 1), end_date=date(2027, 6, 1))
        response = self.client.get(LIST_URL + "?date_from=2026-01-01&date_to=2026-12-31").data["data"]
        self.assertEqual(response["count"], 1)
        self.assertEqual(response["results"][0]["plan_number"], late.plan_number)

    def test_list_filters_missed_only(self):
        with_missed = self._plan(status=InstallmentPlanStatus.ACTIVE)
        self._item(with_missed, 1, date(2025, 1, 14), Decimal("1000000.00"), status=InstallmentItemStatus.MISSED)
        self._item(with_missed, 2, date(2026, 1, 14), Decimal("1000000.00"))
        clean = self._plan(status=InstallmentPlanStatus.ACTIVE)
        self._item(clean, 1, date(2025, 1, 14), Decimal("1000000.00"))

        missed = self.client.get(LIST_URL + "?missed_only=true").data["data"]
        self.assertEqual(missed["count"], 1)
        self.assertEqual(missed["results"][0]["plan_number"], with_missed.plan_number)

        not_missed = self.client.get(LIST_URL + "?missed_only=false").data["data"]
        self.assertEqual(not_missed["count"], 1)
        self.assertEqual(not_missed["results"][0]["plan_number"], clean.plan_number)

    def test_list_search_matches_plan_policy_and_policyholder(self):
        plan = self._plan(status=InstallmentPlanStatus.ACTIVE)
        other_partner = Partner.objects.create(
            partner_number="ZIC-MIP-L-P-0002",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Second Policyholder",
            email="second.policyholder@example.com",
            mobile_number="+255711800003",
            phone="+255711800003",
        )
        other_policy = self._policy("POL-MIP-SEARCH-0002", "QT-MIP-SEARCH-0002", "PROP-MIP-SEARCH-0002", partner=other_partner)
        self._plan(policy=other_policy, status=InstallmentPlanStatus.ACTIVE, partner=other_partner)

        for query in (plan.plan_number, self.policy.policy_number, "List Policyholder One"):
            response = self.client.get(f"{LIST_URL}?q={query}").data["data"]
            self.assertEqual(response["count"], 1, query)
            self.assertEqual(response["results"][0]["plan_number"], plan.plan_number)

    def test_list_sorts_and_paginates(self):
        early = self._plan(status=InstallmentPlanStatus.ACTIVE, start_date=date(2024, 6, 1), end_date=date(2025, 6, 1))
        late = self._plan(status=InstallmentPlanStatus.ACTIVE, start_date=date(2026, 6, 1), end_date=date(2027, 6, 1))
        self._plan(status=InstallmentPlanStatus.ACTIVE, start_date=date(2025, 6, 1), end_date=date(2026, 6, 1))

        sorted_rows = self.client.get(LIST_URL + "?sort=-start_date").data["data"]["results"]
        self.assertEqual(sorted_rows[0]["plan_number"], late.plan_number)
        self.assertEqual(sorted_rows[-1]["plan_number"], early.plan_number)

        page = self.client.get(LIST_URL + "?page=1&page_size=2").data["data"]
        self.assertEqual(page["count"], 3)
        self.assertEqual(len(page["results"]), 2)
        self.assertTrue(page["next"])
        self.assertFalse(page["previous"])

    # ------------------------------------------------------------------
    # KPIs
    # ------------------------------------------------------------------

    def test_kpis_math_is_correct(self):
        today = timezone.localdate()
        active = self._plan(status=InstallmentPlanStatus.ACTIVE)
        self._item(active, 1, today - timedelta(days=60), Decimal("1000000.00"))
        self._item(active, 2, today + timedelta(days=30), Decimal("1000000.00"))
        self._item(active, 3, today + timedelta(days=60), Decimal("1000000.00"), status=InstallmentItemStatus.PAYMENT_PENDING)

        completed = self._plan(status=InstallmentPlanStatus.COMPLETED)
        self._item(completed, 1, today - timedelta(days=90), Decimal("1000000.00"), status=InstallmentItemStatus.PAID)
        self._item(completed, 2, today - timedelta(days=30), Decimal("1000000.00"), status=InstallmentItemStatus.PAID)

        missed = self._plan(status=InstallmentPlanStatus.CREATED)
        self._item(missed, 1, today - timedelta(days=120), Decimal("1000000.00"), status=InstallmentItemStatus.MISSED)
        self._item(missed, 2, today - timedelta(days=90), Decimal("1000000.00"))

        response = self.client.get(KPIS_URL)
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["total_plans_active"], 1)
        self.assertEqual(data["total_upcoming_payouts"], 2)
        self.assertEqual(data["missed_payments_count"], 1)
        self.assertEqual(data["completed_plans_count"], 1)
        self.assertIn("timestamp", data)

    def test_kpis_respect_list_filters(self):
        self._plan(status=InstallmentPlanStatus.ACTIVE)
        self._plan(status=InstallmentPlanStatus.COMPLETED)
        response = self.client.get(KPIS_URL + "?status=ACTIVE")
        data = response.data["data"]
        self.assertEqual(data["total_plans_active"], 1)
        self.assertEqual(data["completed_plans_count"], 0)
        self.assertEqual(data["filters_applied"]["status"], "ACTIVE")

    def test_kpis_missed_count_is_filterable(self):
        plan = self._plan(status=InstallmentPlanStatus.ACTIVE)
        self._item(plan, 1, date(2025, 1, 14), Decimal("1000000.00"), status=InstallmentItemStatus.MISSED)
        self._plan(status=InstallmentPlanStatus.ACTIVE)
        response = self.client.get(KPIS_URL + "?missed_only=true")
        data = response.data["data"]
        self.assertEqual(data["missed_payments_count"], 1)
        self.assertEqual(data["total_plans_active"], 1)

    # ------------------------------------------------------------------
    # Detail
    # ------------------------------------------------------------------

    def test_detail_includes_children_payment_history_and_allowed_actions(self):
        plan = self._plan(status=InstallmentPlanStatus.ACTIVE)
        item_one = self._item(plan, 1, date(2025, 1, 14), Decimal("1000000.00"))
        item_two = self._item(plan, 2, date(2026, 1, 14), Decimal("1000000.00"))
        self._pay(item_one)

        response = self.client.get(DETAIL_URL.format(plan_id=plan.pk))
        self.assertEqual(response.status_code, 200, response.data)
        detail = response.data["data"]
        self.assertEqual(detail["plan_number"], plan.plan_number)
        self.assertEqual(len(detail["items"]), 2)
        self.assertEqual(len(detail["payment_history"]), 1)
        self.assertEqual(detail["payment_history"][0]["installment_number"], 1)
        self.assertEqual(detail["payment_history"][0]["amount"], "1000000.00")
        self.assertTrue(detail["payment_history"][0]["requisition_number"])
        self.assertIn("audit_timeline", detail)
        self.assertEqual(detail["allowed_actions"], ["view", "print", "cancel"])

        items_by_status = {item["status"]: item for item in detail["items"]}
        self.assertEqual(items_by_status["PAID"]["allowed_actions"], ["view", "reverse"])
        self.assertEqual(items_by_status["SCHEDULED"]["allowed_actions"], ["view", "process_payment"])
        self.assertEqual(item_two.installment_number, 2)

    def test_detail_unknown_plan_returns_structured_404(self):
        response = self.client.get(DETAIL_URL.format(plan_id=uuid4()))
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.data["error_code"], "INSTALLMENT_PLAN_NOT_FOUND")

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def test_export_respects_filters(self):
        self._plan(status=InstallmentPlanStatus.ACTIVE)
        self._plan(status=InstallmentPlanStatus.COMPLETED)
        response = self.client.get(EXPORT_URL + "?status=ACTIVE")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv; charset=utf-8")
        self.assertIn("attachment; filename=", response["Content-Disposition"])
        lines = response.content.decode("utf-8").splitlines()
        self.assertEqual(
            lines[0],
            "Plan Number,Policy Number,Policyholder Name,Total Amount,Paid Amount,Balance,Status,Start Date,End Date",
        )
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[1].split(",")[6], "Active")

    def test_export_reflects_paid_and_balance(self):
        plan = self._plan(status=InstallmentPlanStatus.ACTIVE)
        item = self._item(plan, 1, date(2025, 1, 14), Decimal("1000000.00"))
        self._item(plan, 2, date(2026, 1, 14), Decimal("1000000.00"))
        self._pay(item)
        response = self.client.get(EXPORT_URL)
        row = response.content.decode("utf-8").splitlines()[1].split(",")
        self.assertEqual(row[3], "2000000.00")
        self.assertEqual(row[4], "1000000.00")
        self.assertEqual(row[5], "1000000.00")
        self.assertEqual(row[6], "Active")

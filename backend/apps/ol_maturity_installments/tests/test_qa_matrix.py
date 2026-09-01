"""Prompt 10 QA matrix: lifecycle paths, permission matrix, audit matrix, idempotency, and security hardening."""

from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.documents.models import BrandingConfiguration, DocumentTemplate
from apps.documents.services.engine import DocumentTypeRegistry
from apps.governance.models import AuditLog
from apps.ol_maturity_installments.events import (
    INSTALLMENT_PAYMENT_DUE,
    INSTALLMENT_PAYMENT_MISSED,
    INSTALLMENT_PLAN_COMPLETED,
    INSTALLMENT_PLAN_CREATED,
)
from apps.ol_maturity_installments.models import (
    InstallmentItemStatus,
    InstallmentPlanStatus,
    OLInstallmentItem,
    OLMaturityInstallmentPlan,
)
from apps.ol_maturity_installments.services.lifecycle import (
    cancel_installment_plan,
    detect_missed_installments,
    reverse_item_payment,
)
from apps.ol_maturity_installments.services.payment import confirm_item_payment, process_item_payment
from apps.ol_maturity_installments.services.reconciliation import (
    validate_audit_consistency,
    validate_plan_reconciliation,
)
from apps.ol_parameters.models import OLAnticipatedEndowmentInstallmentRate
from apps.ol_policies.models import Policy, PolicyNotificationLog
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.ordinary_life.models import OLProduct
from apps.partners.models import Partner, PartnerBankAccount
from apps.users.models import UserGroup

CREATE_URL = "/api/v1/ol/maturity-installments/create/"
LIST_URL = "/api/v1/ol/maturity-installments/"
DETAIL_URL = "/api/v1/ol/maturity-installments/{plan_id}/"
KPIS_URL = "/api/v1/ol/maturity-installments/kpis/"
EXPORT_URL = "/api/v1/ol/maturity-installments/export/"
OPTIONS_FREQ_URL = "/api/v1/ol/maturity-installments/options/frequencies/"
RECON_URL = "/api/v1/ol/maturity-installments/{plan_id}/reconciliation/"
PROCESS_URL = "/api/v1/ol/maturity-installments/items/{item_id}/process-payment/"
CONFIRM_URL = "/api/v1/ol/maturity-installments/items/{item_id}/confirm-payment/"
REVERSE_URL = "/api/v1/ol/maturity-installments/items/{item_id}/reverse-payment/"
CANCEL_URL = "/api/v1/ol/maturity-installments/plans/{plan_id}/cancel/"
PRINT_SCHEDULE_URL = "/api/v1/ol/maturity-installments/{plan_id}/print-schedule/"


def _money(value):
    return f"{value:.2f}"


class _MatrixBase(TestCase):
    """Shared fixtures: actor, partner, agent, product, rate, and plan/item builders."""

    client_class = APIClient

    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.user = User.objects.create_superuser(
            username="qa-matrix-admin",
            email="qa.matrix.admin@example.com",
            password="Strong-qa-matrix-password-123!",
        )
        cls.partner = Partner.objects.create(
            partner_number="ZIC-MIP-QA-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="QA Matrix Policyholder",
            email="qa.matrix@example.com",
            mobile_number="+255711700001",
            phone="+255711700001",
        )
        cls.agent = Partner.objects.create(
            partner_number="ZIC-MIP-QA-A-0001",
            partner_type="AGENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="QA Matrix Agent",
            email="qa.matrix.agent@example.com",
        )
        product = OLProduct.objects.create(
            code="OL_ENDOWMENT_STANDARD",
            name="Endowment Standard",
            business_area="ORDINARY_LIFE",
            is_active=True,
        )
        OLAnticipatedEndowmentInstallmentRate.objects.create(
            code="MIP-QA-ANNUAL-10",
            name="QA annual rate",
            product=product,
            plan=None,
            installment_type="ANTICIPATED_ENDOWMENT",
            frequency="ANNUAL",
            term_from=10,
            term_to=10,
            rate_factor=Decimal("10.00000000"),
            currency="",
            is_active=True,
            effective_from=date(2026, 1, 1),
            effective_to=None,
        )

    def setUp(self):
        self.client.force_authenticate(self.user)

    def _policy(self, number, *, status="MATURED", maturity_date=None):
        quotation = OLQuotation.objects.create(
            quote_number=f"QT-{number}",
            quote_name=f"Quote {number}",
            quote_date=date.today(),
            partner=self.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number=f"PROP-{number}",
            status="POLICY_ISSUED",
            partner=self.partner,
            agent_partner=self.agent,
            currency="TZS",
        )
        return Policy.objects.create(
            policy_number=f"POL-{number}",
            proposal_ref=proposal,
            partner=self.partner,
            agent=self.agent,
            product_plan_ref="OL_ENDOWMENT_STANDARD",
            currency="TZS",
            sum_assured=Decimal("25000000.00"),
            premium_amount=Decimal("125000.00"),
            premium_frequency="ANNUALLY",
            term_years=10,
            risk_commencement_date=date(2016, 1, 15),
            maturity_date=maturity_date or date(2026, 1, 14),
            status=status,
        )

    def _plan(self, policy, *, status=InstallmentPlanStatus.CREATED):
        return OLMaturityInstallmentPlan.objects.create(
            policy_ref=policy,
            partner=policy.partner,
            currency="TZS",
            total_maturity_value=Decimal("25000000.00"),
            total_payable_amount=Decimal("25000000.00"),
            installment_count=2,
            frequency="ANNUAL",
            start_date=date(2025, 1, 14),
            end_date=date(2026, 1, 14),
            status=status,
            created_by=self.user,
        )

    def _item(self, plan, number, *, due_date=None, status=InstallmentItemStatus.SCHEDULED):
        return OLInstallmentItem.objects.create(
            plan_ref=plan,
            installment_number=number,
            due_date=due_date or (date(2025, 1, 14) if number == 1 else date(2026, 1, 14)),
            amount=Decimal("12500000.00"),
            status=status,
            created_by=self.user,
        )

    def _bank(self, partner):
        return PartnerBankAccount.objects.create(
            partner=partner,
            bank_name="NBC Bank",
            branch_name="Dar es Salaam",
            account_name="QA Matrix Policyholder",
            account_number="0123456789",
            swift_code="NLCBTZTX",
            iban="TZ0010123456789",
            currency="TZS",
            is_primary=True,
            is_verified=True,
        )


class LifecycleMatrixTestCase(_MatrixBase):
    def test_happy_path_policy_mature_to_create_to_completed(self):
        policy = self._policy("MIP-QA-HAPPY-0001", status="MATURED", maturity_date=date(2016, 1, 14))
        self._bank(self.partner)

        response = self.client.post(
            CREATE_URL,
            {"policy_id": str(policy.pk), "frequency": "ANNUAL", "term_years": 10},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="qa-happy-path-001",
        )
        self.assertEqual(response.status_code, 201)
        plan = OLMaturityInstallmentPlan.objects.get(pk=response.data["data"]["id"])
        self.assertEqual(plan.status, InstallmentPlanStatus.CREATED)
        self.assertEqual(plan.installment_count, 10)
        self.assertTrue(
            DomainEvent.objects.filter(event_type=INSTALLMENT_PLAN_CREATED, aggregate_id=str(plan.pk)).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(action="CREATE", app_label="ol_maturity_installments", object_id=str(plan.pk)).exists()
        )

        today = date.today()
        for number in range(1, plan.installment_count + 1):
            item = plan.items.get(installment_number=number)
            if item.due_date > today:
                item.due_date = today
                item.save(update_fields=["due_date"])
            process_item_payment(item_id=item.pk, actor=self.user)
            confirm_item_payment(item_id=item.pk, actor=self.user)

        plan.refresh_from_db()
        self.assertEqual(plan.status, InstallmentPlanStatus.COMPLETED)
        self.assertIsNotNone(plan.completed_at)
        self.assertTrue(
            DomainEvent.objects.filter(event_type=INSTALLMENT_PLAN_COMPLETED, aggregate_id=str(plan.pk)).exists()
        )
        report = validate_plan_reconciliation(plan_id=plan.pk)
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.discrepancies, [])
        self.assertEqual(report.paid_amount, _money(plan.total_payable_amount))
        self.assertEqual(report.missing_amount, "0.00")

    def test_missed_path_active_plan_to_missed_notification(self):
        policy = self._policy("MIP-QA-MISS-0001", status="MATURED")
        plan = self._plan(policy)
        self._item(plan, 1)
        self._item(plan, 2)
        self._bank(self.partner)

        item_one = plan.items.get(installment_number=1)
        process_item_payment(item_id=item_one.pk, actor=self.user)
        confirm_item_payment(item_id=item_one.pk, actor=self.user)
        plan.refresh_from_db()
        self.assertEqual(plan.status, InstallmentPlanStatus.ACTIVE)

        result = detect_missed_installments(as_of=date(2026, 2, 1), plan_id=plan.pk, actor=self.user)
        self.assertEqual(result.missed, 1)
        item_two = plan.items.get(installment_number=2)
        self.assertEqual(item_two.status, InstallmentItemStatus.MISSED)
        self.assertTrue(
            DomainEvent.objects.filter(event_type=INSTALLMENT_PAYMENT_MISSED, aggregate_id=str(plan.pk)).exists()
        )
        self.assertTrue(
            PolicyNotificationLog.objects.filter(policy=policy, event_type=INSTALLMENT_PAYMENT_MISSED).exists()
        )

    def test_reversal_path_paid_to_reversed_status_restored(self):
        policy = self._policy("MIP-QA-REV-0001", status="MATURED")
        plan = self._plan(policy)
        item = self._item(plan, 1, due_date=date.today())
        self._bank(self.partner)

        process_item_payment(item_id=item.pk, actor=self.user)
        confirm_item_payment(item_id=item.pk, actor=self.user)
        item.refresh_from_db()
        self.assertEqual(item.status, InstallmentItemStatus.PAID)

        reversed_item, requisition = reverse_item_payment(
            item_id=item.pk, reason="Disbursed in error.", actor=self.user
        )
        self.assertEqual(reversed_item.status, InstallmentItemStatus.SCHEDULED)
        self.assertEqual(requisition.status, "REVERSED")
        self.assertIsNone(reversed_item.payment_requisition_ref_id)
        audit = AuditLog.objects.filter(
            action="INSTALLMENT_PAYMENT_REVERSED", object_id=str(item.pk)
        ).latest("created_at")
        self.assertEqual(audit.before_state["status"], "PAID")
        self.assertEqual(audit.after_state["status"], "SCHEDULED")

    def test_cancellation_path_created_to_cancelled_audit_trail(self):
        policy = self._policy("MIP-QA-CANC-0001", status="MATURED")
        plan = self._plan(policy)
        item_one = self._item(plan, 1)
        item_two = self._item(plan, 2)

        cancelled = cancel_installment_plan(plan_id=plan.pk, reason="Policyholder opted out.", actor=self.user)
        self.assertEqual(cancelled.status, InstallmentPlanStatus.CANCELLED)
        item_one.refresh_from_db()
        item_two.refresh_from_db()
        self.assertEqual(item_one.status, InstallmentItemStatus.WAIVED)
        self.assertEqual(item_two.status, InstallmentItemStatus.WAIVED)
        self.assertTrue(
            AuditLog.objects.filter(action="INSTALLMENT_PLAN_CANCELLED", object_id=str(plan.pk)).exists()
        )
        self.assertTrue(
            AuditLog.objects.filter(action="INSTALLMENT_ITEM_WAIVED", object_id=str(item_one.pk)).exists()
        )


class AuditMatrixTestCase(_MatrixBase):
    def test_full_lifecycle_every_transition_has_audit_row(self):
        policy = self._policy("MIP-QA-AUDIT-0001", status="MATURED", maturity_date=date(2016, 1, 14))
        self._bank(self.partner)
        response = self.client.post(
            CREATE_URL,
            {"policy_id": str(policy.pk), "frequency": "ANNUAL", "term_years": 10},
            format="json",
            HTTP_X_IDEMPOTENCY_KEY="qa-audit-lifecycle-001",
        )
        self.assertEqual(response.status_code, 201)
        plan = OLMaturityInstallmentPlan.objects.get(pk=response.data["data"]["id"])

        item_one = plan.items.get(installment_number=1)
        process_item_payment(item_id=item_one.pk, actor=self.user)
        confirm_item_payment(item_id=item_one.pk, actor=self.user)
        plan.refresh_from_db()
        self.assertEqual(plan.status, InstallmentPlanStatus.ACTIVE)

        plan_actions = set(
            AuditLog.objects.filter(
                app_label="ol_maturity_installments", object_id=str(plan.pk)
            ).values_list("action", flat=True)
        )
        self.assertTrue({"CREATE", "INSTALLMENT_PLAN_ACTIVATED"}.issubset(plan_actions))
        item_actions = set(
            AuditLog.objects.filter(
                app_label="ol_maturity_installments", object_id=str(item_one.pk)
            ).values_list("action", flat=True)
        )
        self.assertTrue({"INSTALLMENT_PAYMENT_PROCESSED", "INSTALLMENT_PAYMENT_CONFIRMED"}.issubset(item_actions))

        report = validate_audit_consistency(plan_id=plan.pk)
        self.assertEqual(report.status, "PASS", msg=report.to_dict())
        self.assertEqual(report.findings, [])

    def test_financial_consistency_partial_then_full_payment(self):
        policy = self._policy("MIP-QA-FIN-0001", status="MATURED")
        plan = self._plan(policy)
        self._item(plan, 1)
        self._item(plan, 2)
        self._bank(self.partner)

        item_one = plan.items.get(installment_number=1)
        process_item_payment(item_id=item_one.pk, actor=self.user)
        confirm_item_payment(item_id=item_one.pk, actor=self.user)
        partial = validate_plan_reconciliation(plan_id=plan.pk)
        self.assertEqual(partial.status, "FAIL")
        self.assertTrue(any(d.code == "MISSING_PAYMENTS" for d in partial.discrepancies))
        self.assertEqual(partial.paid_amount, _money(Decimal("12500000.00")))
        self.assertNotEqual(partial.missing_amount, "0.00")

        item_two = plan.items.get(installment_number=2)
        process_item_payment(item_id=item_two.pk, actor=self.user)
        confirm_item_payment(item_id=item_two.pk, actor=self.user)
        plan.refresh_from_db()
        self.assertEqual(plan.status, InstallmentPlanStatus.COMPLETED)
        full = validate_plan_reconciliation(plan_id=plan.pk)
        self.assertEqual(full.status, "PASS")
        self.assertEqual(full.discrepancies, [])
        self.assertEqual(full.paid_amount, _money(plan.total_payable_amount))
        self.assertEqual(full.missing_amount, "0.00")
        self.assertEqual(full.paid_item_count, plan.installment_count)


class IdempotencyMatrixTestCase(_MatrixBase):
    def test_plan_creation_retry_returns_same_plan(self):
        policy = self._policy("MIP-QA-IDEM-CREATE-0001", status="MATURED")
        payload = {"policy_id": str(policy.pk), "frequency": "ANNUAL", "term_years": 10}
        first = self.client.post(CREATE_URL, payload, format="json", HTTP_X_IDEMPOTENCY_KEY="qa-create-retry-001")
        second = self.client.post(CREATE_URL, payload, format="json", HTTP_X_IDEMPOTENCY_KEY="qa-create-retry-001")
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(first.data["data"]["id"], second.data["data"]["id"])
        self.assertEqual(
            OLMaturityInstallmentPlan.objects.filter(idempotency_key="qa-create-retry-001").count(), 1
        )
        self.assertEqual(
            DomainEvent.objects.filter(event_type=INSTALLMENT_PLAN_CREATED, aggregate_id=str(first.data["data"]["id"])).count(),
            1,
        )

    def test_payment_processing_retry_returns_same_requisition(self):
        policy = self._policy("MIP-QA-IDEM-PROC-0001", status="MATURED")
        plan = self._plan(policy)
        self._item(plan, 1)
        self._bank(self.partner)
        item = plan.items.get(installment_number=1)

        _item_a, requisition_a, created_a = process_item_payment(item_id=item.pk, actor=self.user)
        _item_b, requisition_b, created_b = process_item_payment(item_id=item.pk, actor=self.user)
        self.assertTrue(created_a)
        self.assertFalse(created_b)
        self.assertEqual(requisition_a.pk, requisition_b.pk)
        self.assertEqual(
            DomainEvent.objects.filter(event_type=INSTALLMENT_PAYMENT_DUE, aggregate_id=str(plan.pk)).count(), 1
        )

    def test_missed_detection_rerun_is_safe(self):
        policy = self._policy("MIP-QA-IDEM-MISS-0001", status="MATURED")
        plan = self._plan(policy)
        self._item(plan, 1)

        first = detect_missed_installments(as_of=date(2026, 2, 1), plan_id=plan.pk, actor=self.user)
        second = detect_missed_installments(as_of=date(2026, 2, 1), plan_id=plan.pk, actor=self.user)
        self.assertEqual(first.missed, 1)
        self.assertEqual(second.missed, 0)
        self.assertEqual(
            DomainEvent.objects.filter(event_type=INSTALLMENT_PAYMENT_MISSED, aggregate_id=str(plan.pk)).count(), 1
        )
        after_first = PolicyNotificationLog.objects.filter(
            policy=policy, event_type=INSTALLMENT_PAYMENT_MISSED
        ).count()
        self.assertGreaterEqual(after_first, 1)
        after_second = PolicyNotificationLog.objects.filter(
            policy=policy, event_type=INSTALLMENT_PAYMENT_MISSED
        ).count()
        self.assertEqual(after_second, after_first)


class PermissionMatrixTestCase(_MatrixBase):
    ROLE_EXPECTATIONS = {
        "plain": dict(view=403, create=403, process=403, confirm=403, reverse=403, print=403, cancel=403),
        "viewer": dict(view=200, create=403, process=403, confirm=403, reverse=403, print=403, cancel=403),
        "handler": dict(view=200, create=201, process=201, confirm=200, reverse=200, print=201, cancel=403),
        "admin": dict(view=200, create=201, process=201, confirm=200, reverse=200, print=201, cancel=200),
        "superuser": dict(view=200, create=201, process=201, confirm=200, reverse=200, print=201, cancel=200),
    }

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        call_command("seed_ol_maturity_installment_permissions", verbosity=0)
        User = get_user_model()
        cls.users = {
            "superuser": User.objects.create_superuser(
                username="qa-perm-super",
                email="qa.perm.super@example.com",
                password="Strong-qa-perm-password-123!",
            ),
            "plain": User.objects.create_user(
                username="qa-perm-plain",
                email="qa.perm.plain@example.com",
                password="Strong-qa-perm-password-123!",
            ),
            "viewer": User.objects.create_user(
                username="qa-perm-viewer",
                email="qa.perm.viewer@example.com",
                password="Strong-qa-perm-password-123!",
            ),
            "handler": User.objects.create_user(
                username="qa-perm-handler",
                email="qa.perm.handler@example.com",
                password="Strong-qa-perm-password-123!",
            ),
            "admin": User.objects.create_user(
                username="qa-perm-admin",
                email="qa.perm.admin@example.com",
                password="Strong-qa-perm-password-123!",
            ),
        }
        cls.users["viewer"].groups.add(UserGroup.objects.get(code="OL_MATURITY_INSTALLMENTS_VIEWER"))
        cls.users["handler"].groups.add(UserGroup.objects.get(code="OL_MATURITY_INSTALLMENTS_HANDLER"))
        cls.users["admin"].groups.add(UserGroup.objects.get(code="OL_MATURITY_INSTALLMENTS_ADMINISTRATOR"))

        for definition in DocumentTypeRegistry.definitions():
            if definition.document_type not in {"OL_MATURITY_SCHEDULE", "OL_MATURITY_PAYMENT_ADVICE"}:
                continue
            DocumentTemplate.objects.update_or_create(
                code=definition.template_code,
                version=1,
                defaults={
                    "name": definition.title,
                    "document_type": definition.document_type,
                    "layout_template_path": definition.layout_template_path,
                    "variables_schema": definition.variables_schema,
                    "branding_config_reference": "COMPANY_BRANDING",
                    "is_active": True,
                },
            )
        BrandingConfiguration.objects.update_or_create(
            code="COMPANY_BRANDING",
            version=1,
            defaults={
                "company_name": "Zanzibar Insurance Corporation",
                "address": "Bima House, Mlandege Road, Zanzibar City",
                "phone": "+255 659 072 500",
                "email": "info@zic.co.tz",
                "registration_number": "ZIC-REG-001",
                "footer_legal_text": "Official ZIC maturity installment document.",
                "accent_colors": {"primary": "#183a91", "accent": "#d94754", "table_header": "#edf1f4"},
                "is_active": True,
            },
        )

    def test_actions_gated_by_ol_maturity_installments_permissions(self):
        for role, expected in self.ROLE_EXPECTATIONS.items():
            with self.subTest(role=role):
                user = self.users[role]
                policy = self._policy(f"MIP-QA-PERM-{role}", status="MATURED", maturity_date=date(2016, 1, 14))
                plan = self._plan(policy)
                item = self._item(plan, 1, due_date=date.today())
                self._item(plan, 2)
                self._bank(policy.partner)
                client = APIClient()
                client.force_authenticate(user)

                read_statuses = [
                    client.get(LIST_URL).status_code,
                    client.get(KPIS_URL).status_code,
                    client.get(EXPORT_URL).status_code,
                    client.get(DETAIL_URL.format(plan_id=plan.pk)).status_code,
                    client.get(RECON_URL.format(plan_id=plan.pk)).status_code,
                    client.get(OPTIONS_FREQ_URL).status_code,
                ]
                self.assertEqual(read_statuses, [expected["view"]] * 6)

                create = client.post(
                    CREATE_URL,
                    {"policy_id": str(policy.pk), "frequency": "ANNUAL", "term_years": 10},
                    format="json",
                    HTTP_X_IDEMPOTENCY_KEY=f"qa-perm-{role}",
                )
                self.assertEqual(create.status_code, expected["create"])

                process = client.post(PROCESS_URL.format(item_id=item.pk), {}, format="json")
                self.assertEqual(process.status_code, expected["process"])

                confirm = client.post(CONFIRM_URL.format(item_id=item.pk), {}, format="json")
                self.assertEqual(confirm.status_code, expected["confirm"])

                reverse = client.post(
                    REVERSE_URL.format(item_id=item.pk),
                    {"reason": "Reversal in permission matrix."},
                    format="json",
                )
                self.assertEqual(reverse.status_code, expected["reverse"])

                print_response = client.post(PRINT_SCHEDULE_URL.format(plan_id=plan.pk), {}, format="json")
                self.assertEqual(print_response.status_code, expected["print"])

                cancel = client.post(
                    CANCEL_URL.format(plan_id=plan.pk),
                    {"reason": "Cancellation in permission matrix."},
                    format="json",
                )
                self.assertEqual(cancel.status_code, expected["cancel"])


class SecurityHardeningTestCase(_MatrixBase):
    def test_csv_export_neutralizes_formula_injection(self):
        policy = self._policy("MIP-QA-SEC-0001", status="MATURED")
        hostile_cells = ("=1+1", "+SUM(A1:A9)", "-2+3", "@import")
        for index, name in enumerate(hostile_cells, start=1):
            partner = Partner.objects.create(
                partner_number=f"ZIC-MIP-SEC-P-000{index}",
                partner_type="CLIENT",
                partner_category="INDIVIDUAL",
                party_type="INDIVIDUAL",
                legal_name=name,
                email=f"sec0{index}@example.com",
                mobile_number=f"+25571180000{index}",
            )
            plan = self._plan(policy)
            plan.partner = partner
            plan.save(update_fields=["partner"])

        response = self.client.get(EXPORT_URL)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        content = response.content.decode("utf-8")
        self.assertIn("'=1+1", content)
        self.assertIn("'+SUM(A1:A9)", content)
        self.assertIn("'-2+3", content)
        self.assertIn("'@import", content)
        self.assertNotIn(",=1+1", content)
        self.assertNotIn(",+SUM(A1:A9)", content)
        self.assertNotIn(",-2+3", content)
        self.assertNotIn(",@import", content)

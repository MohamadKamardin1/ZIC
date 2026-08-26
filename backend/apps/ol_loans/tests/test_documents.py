from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase
from pypdf import PdfReader
from rest_framework.test import APIClient

from apps.documents.models import BrandingConfiguration, DocumentInstance, DocumentTemplate
from apps.documents.services.engine import DocumentTypeRegistry
from apps.governance.models import AuditLog
from apps.governance.services.audit_service import AuditService
from apps.ol_loans.models import LoanScheduleStatus, LoanStatus, OLLoan, OLLoanSchedule
from apps.ol_loans.services.audit_consistency import verify_loan_audit_consistency
from apps.ol_policies.models import Policy
from apps.ol_proposals.models import OLProposal
from apps.ol_quotations.models import OLQuotation
from apps.partners.models import Partner


class OLLoanDocumentsTestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        User = get_user_model()
        cls.admin = User.objects.create_superuser(
            username="ol-loan-document-admin",
            email="ol-loan-document-admin@example.com",
            password="Strong-loan-document-password-123!",
        )
        cls.denied_user = User.objects.create_user(
            username="ol-loan-document-viewer",
            email="ol-loan-document-viewer@example.com",
            password="Strong-loan-document-viewer-password-123!",
        )
        cls.partner = Partner.objects.create(
            partner_number="ZIC-LOAN-DOC-P-0001",
            partner_type="CLIENT",
            partner_category="INDIVIDUAL",
            party_type="INDIVIDUAL",
            legal_name="Document Test Borrower",
            email="document.borrower@example.com",
        )
        cls.agent = Partner.objects.create(
            partner_number="ZIC-LOAN-DOC-A-0001",
            partner_type="AGENT",
            partner_category="INTERMEDIARY",
            party_type="ORGANIZATION",
            legal_name="Document Test Agency",
            email="document.agency@example.com",
        )
        quotation = OLQuotation.objects.create(
            quote_number="QT-LOAN-DOC-001",
            quote_name="Loan document test",
            quote_date=date.today(),
            partner=cls.partner,
            currency="TZS",
        )
        proposal = OLProposal.objects.create(
            quotation=quotation,
            proposal_number="PROP-LOAN-DOC-001",
            status="CONVERTED",
            partner=cls.partner,
            currency="TZS",
            prospect_snapshot={},
            financial_summary_snapshot={},
        )
        policy = Policy.objects.create(
            proposal_ref=proposal,
            partner=cls.partner,
            agent=cls.agent,
            product_plan_ref="OL_DOC_PLAN",
            currency="TZS",
            sum_assured=Decimal("10000000.00"),
            premium_amount=Decimal("100000.00"),
            premium_frequency="MONTHLY",
            term_years=10,
            risk_commencement_date=date.today(),
            maturity_date=date(date.today().year + 10, date.today().month, date.today().day),
            status="ACTIVE",
            contract_snapshot={"product_name": "Document Protection Plan", "branch_name": "ZIC Main Branch"},
        )
        cls.loan = OLLoan.objects.create(
            loan_number="LOAN-DOC-001",
            policy_ref=policy,
            partner=cls.partner,
            currency="TZS",
            principal_amount=Decimal("1000000.00"),
            cash_value_snapshot=Decimal("1500000.00"),
            disbursed_amount=Decimal("1000000.00"),
            repayment_mode="EQUAL_INSTALLMENT",
            interest_rate=Decimal("0.12000000"),
            compounding_frequency="MONTHLY",
            term_months=36,
            disbursement_date=date(2026, 1, 15),
            maturity_date=date(2029, 1, 15),
            status=LoanStatus.DEFAULTED,
            outstanding_balance=Decimal("900000.00"),
            reason="Education support",
        )
        for installment in range(1, 41):
            principal = Decimal("25000.00")
            interest = Decimal("2500.00")
            penalty = Decimal("0.00")
            OLLoanSchedule.objects.create(
                loan=cls.loan,
                installment_number=installment,
                due_date=date(2026, 2, 15) + timedelta(days=30 * (installment - 1)),
                principal_due=principal,
                interest_due=interest,
                penalty_due=penalty,
                amount_paid=Decimal("0.00"),
                balance=principal + interest,
                status=LoanScheduleStatus.OVERDUE if installment == 1 else LoanScheduleStatus.PENDING,
            )
        for definition in DocumentTypeRegistry.definitions():
            if definition.document_type not in {"OL_LOAN_AGREEMENT", "OL_LOAN_SCHEDULE"}:
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
                "footer_legal_text": "Official ZIC loan document.",
                "accent_colors": {"primary": "#183a91", "accent": "#d94754", "table_header": "#edf1f4"},
                "is_active": True,
            },
        )
        AuditService.log_action(
            action="LOAN_CREATED",
            instance=cls.loan,
            actor=cls.admin,
            reason="Seeded loan action for audit consistency verification.",
            source_channel="API",
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(self.admin)

    def _render(self, suffix):
        response = self.client.post(f"/api/v1/ol/loans/{self.loan.pk}/{suffix}/", {}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        payload = response.data["data"]
        self.assertTrue(payload["signed_download_url"])
        self.assertTrue(payload["preview_url"])
        return payload

    def _download(self, payload):
        signed = urlparse(payload["signed_download_url"])
        ticket = parse_qs(signed.query)["ticket"][0]
        response = APIClient().get(f"{signed.path}?ticket={ticket}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "application/pdf")
        return b"".join(response.streaming_content)

    def test_agreement_pdf_contains_required_blocks_logo_and_defaulted_watermark(self):
        payload = self._render("print-agreement")
        pdf_bytes = self._download(payload)
        reader = PdfReader(BytesIO(pdf_bytes))
        self.assertGreaterEqual(len(reader.pages), 2)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        for expected in (
            "LOAN AGREEMENT",
            "Parties to the agreement",
            "Document Test Borrower",
            "LOAN-DOC-001",
            "Policy number",
            "Loan terms and principal",
            "Repayment schedule summary",
            "Principal amount",
            "Interest rate",
            "Signature & Date",
            "DEFAULTED",
            "Page 1 of",
            "Template v1",
            "Zanzibar Insurance Corporation",
        ):
            self.assertIn(expected, text)
        self.assertTrue(any(getattr(page, "images", []) for page in reader.pages))
        instance = DocumentInstance.objects.get(pk=payload["id"])
        self.assertEqual(instance.document_type, "OL_LOAN_AGREEMENT")
        self.assertEqual(instance.template_version, 1)
        self.assertEqual(instance.source_type, "ol_loans.olloan")
        self.assertEqual(instance.source_object_id, str(self.loan.pk))
        self.assertTrue(AuditLog.objects.filter(action="DOCUMENT_GENERATED", object_id=str(instance.pk)).exists())

    def test_schedule_pdf_contains_repeating_installment_headers_and_totals(self):
        payload = self._render("print-schedule")
        pdf_bytes = self._download(payload)
        reader = PdfReader(BytesIO(pdf_bytes))
        self.assertGreaterEqual(len(reader.pages), 2)
        text = "\n".join(page.extract_text() or "" for page in reader.pages)
        for expected in (
            "LOAN REPAYMENT SCHEDULE",
            "Installments",
            "Due date",
            "Principal due",
            "Interest due",
            "Penalty due",
            "Amount paid",
            "Schedule summary",
            "40 installments",
            "Document Test Borrower",
            "Page 1 of",
        ):
            self.assertIn(expected, text)
        self.assertGreaterEqual(text.count("Due date"), 2)
        self.assertEqual(DocumentInstance.objects.get(pk=payload["id"]).page_count, len(reader.pages))

    def test_print_permission_is_enforced(self):
        self.client.force_authenticate(self.denied_user)
        response = self.client.post(f"/api/v1/ol/loans/{self.loan.pk}/print-agreement/", {}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertIn("permission", str(response.data).lower())

    def test_audit_consistency_utility_passes_for_seeded_loan_and_flags_orphan(self):
        report = verify_loan_audit_consistency()
        self.assertTrue(report["passed"], report)
        self.assertEqual(report["loan_count"], 1)
        self.assertEqual(report["audited_loan_count"], 1)
        AuditLog.objects.create(
            user=self.admin,
            action_type="UPDATE",
            entity_type="olloan",
            entity_id=None,
            entity_repr="orphan loan action",
            action="ORPHAN_ACTION",
            app_label="ol_loans",
            model_name="olloan",
            object_id="00000000-0000-0000-0000-000000000000",
            object_repr="orphan loan action",
            source_channel="API",
        )
        failed = verify_loan_audit_consistency()
        self.assertFalse(failed["passed"])
        self.assertEqual(len(failed["orphan_audit_records"]), 1)

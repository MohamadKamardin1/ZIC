from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from apps.dashboard.models import DashboardNotification, DashboardTask
from apps.governance.models import ApprovalRequest, AuditLog
from apps.ordinary_life.models import OLClient, OLNote, OLProduct, OLProposal, OLQuotation
from apps.ordinary_life.services.operations_service import OrdinaryLifeOperationsService
from apps.users.models import User, UserGroup, UserPermission


class OrdinaryLifeOperationsServiceTests(TestCase):
    def setUp(self):
        self.actor = User.objects.create_user(
            username="phase7-operator",
            email="phase7-operator@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
            is_superuser=True,
            user_type="SYSTEM_MANAGER",
        )
        self.proposal = self._proposal()

    def _proposal(self):
        product = OLProduct.objects.create(
            code="OL_PHASE7",
            name="Phase 7 Protection",
            business_area="ORDINARY_LIFE",
            min_age=18,
            max_age=65,
            term_length_years=10,
            is_active=True,
        )
        client = OLClient.objects.create(
            first_name="Asha",
            last_name="Juma",
            date_of_birth=date(1990, 6, 15),
            id_number="P7-CLIENT-0001",
        )
        quotation = OLQuotation.objects.create(
            quotation_number="P7-QUOTE-0001",
            client=client,
            product=product,
            sum_assured="10000000.00",
            premium_amount="12000.00",
            currency="TZS",
            payment_frequency="ANNUAL",
        )
        return OLProposal.objects.create(
            proposal_number="P7-PROP-0001",
            quotation=quotation,
            status="PENDING",
        )

    def test_document_lifecycle_creates_work_items_and_shared_approval_history(self):
        document = OrdinaryLifeOperationsService.create_document(
            proposal=self.proposal,
            document_type="NATIONAL_ID",
            actor=self.actor,
            idempotency_key="p7-document-1",
        )
        self.assertEqual(document.status, "PENDING")
        self.assertTrue(
            DashboardTask.objects.filter(
                owner=self.actor,
                entity_type="OLDocumentRecord",
                entity_id=str(document.pk),
            ).exists()
        )
        self.assertTrue(
            DashboardNotification.objects.filter(
                owner=self.actor,
                external_key=f"ordinary-life-document-{document.pk}-created",
            ).exists()
        )

        uploaded = OrdinaryLifeOperationsService.upload_document(
            document,
            file_reference="s3://ordinary-life/p7/national-id.pdf",
            actor=self.actor,
            reason="Received from the policyholder",
        )
        self.assertEqual(uploaded.status, "UPLOADED")
        approval = OrdinaryLifeOperationsService.submit_document_verification(
            uploaded,
            actor=self.actor,
            comments="Ready for compliance review",
        )
        self.assertEqual(approval.status, "PENDING")
        verified = OrdinaryLifeOperationsService.complete_document_verification(
            approval.pk,
            reviewer=self.actor,
            comments="Identity document verified",
        )
        self.assertEqual(verified.status, "VERIFIED")
        self.assertEqual(verified.verified_by_id, self.actor.pk)
        self.assertTrue(
            AuditLog.objects.filter(
                app_label="ordinary_life",
                model_name="oldocumentrecord",
                object_id=str(document.pk),
                action="VERIFY_DOCUMENT",
            ).exists()
        )
        self.assertGreaterEqual(
            OrdinaryLifeOperationsService.workflow_history(
                entity_type="ordinary_life.OLDocumentRecord",
                entity_id=document.pk,
                actor=self.actor,
            ).count(),
            4,
        )

    def test_document_verification_rejection_requires_reason_and_can_be_reuploaded(self):
        document = OrdinaryLifeOperationsService.create_document(
            proposal=self.proposal,
            document_type="MEDICAL_REPORT",
            actor=self.actor,
        )
        with self.assertRaises(ValidationError):
            OrdinaryLifeOperationsService.reject_document(document, actor=self.actor)
        rejected = OrdinaryLifeOperationsService.reject_document(
            document,
            actor=self.actor,
            reason="The report is incomplete.",
        )
        self.assertEqual(rejected.status, "REJECTED")
        uploaded = OrdinaryLifeOperationsService.upload_document(
            rejected,
            file_reference="s3://ordinary-life/p7/medical-report-v2.pdf",
            actor=self.actor,
        )
        self.assertEqual(uploaded.status, "UPLOADED")

    def test_document_and_note_idempotency_is_deterministic(self):
        first_document = OrdinaryLifeOperationsService.create_document(
            proposal=self.proposal,
            document_type="CONSENT",
            actor=self.actor,
            idempotency_key="p7-document-idempotent",
        )
        repeated_document = OrdinaryLifeOperationsService.create_document(
            proposal=self.proposal,
            document_type="CONSENT",
            actor=self.actor,
            idempotency_key="p7-document-idempotent",
        )
        self.assertEqual(first_document.pk, repeated_document.pk)
        first_note = OrdinaryLifeOperationsService.add_note(
            proposal=self.proposal,
            content="Customer consent captured.",
            actor=self.actor,
            idempotency_key="p7-note-idempotent",
        )
        repeated_note = OrdinaryLifeOperationsService.add_note(
            proposal=self.proposal,
            content="Customer consent captured.",
            actor=self.actor,
            idempotency_key="p7-note-idempotent",
        )
        self.assertEqual(first_note.pk, repeated_note.pk)
        self.assertEqual(OLNote.objects.filter(idempotency_key="p7-note-idempotent").count(), 1)

    def test_exactly_one_parent_is_required_for_documents_and_notes(self):
        with self.assertRaises(ValidationError):
            OrdinaryLifeOperationsService.create_document(
                document_type="OTHER",
                actor=self.actor,
            )
        with self.assertRaises(ValidationError):
            OrdinaryLifeOperationsService.add_note(
                content="Unattached note",
                actor=self.actor,
            )

    def test_policy_approval_submission_is_idempotent_and_creates_clickable_task(self):
        first = OrdinaryLifeOperationsService.submit_policy_approval(
            self.proposal,
            entity_type="OLProposal",
            action="APPROVE",
            actor=self.actor,
            requested_data={"status": "APPROVED"},
            comments="Ready for business approval",
        )
        repeated = OrdinaryLifeOperationsService.submit_policy_approval(
            self.proposal,
            entity_type="OLProposal",
            action="APPROVE",
            actor=self.actor,
        )
        self.assertEqual(first.pk, repeated.pk)
        self.assertEqual(ApprovalRequest.objects.filter(pk=first.pk).count(), 1)
        task = DashboardTask.objects.get(entity_type="ApprovalRequest", entity_id=str(first.pk))
        self.assertIn(str(self.proposal.pk), task.route)

    def test_audit_history_requires_compliance_permission(self):
        events = OrdinaryLifeOperationsService.audit_history(
            model_name="OLDocumentRecord",
            object_id=self.proposal.pk,
            actor=self.actor,
        )
        self.assertEqual(events.count(), 0)
        viewer = User.objects.create_user(
            username="phase7-viewer",
            email="phase7-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
            user_type="MANAGER",
        )
        with self.assertRaises(PermissionDenied):
            OrdinaryLifeOperationsService.audit_history(
                model_name="OLDocumentRecord",
                object_id=self.proposal.pk,
                actor=viewer,
            )

    def test_module_permission_is_required_and_is_not_inferred_from_authentication(self):
        viewer = User.objects.create_user(
            username="phase7-permission-viewer",
            email="phase7-permission-viewer@example.com",
            password="Strong-pass-123!",
            is_active=True,
            is_approved=True,
            user_type="MANAGER",
        )
        with self.assertRaises(PermissionDenied):
            OrdinaryLifeOperationsService.create_document(
                proposal=self.proposal,
                document_type="PASSPORT",
                actor=viewer,
            )
        permission = UserPermission.objects.create(
            name="Create Ordinary Life records",
            codename="ordinary_life.create",
            module="ORDINARY_LIFE",
            action=UserPermission.Action.CREATE,
        )
        group = UserGroup.objects.create(name="Phase 7 Ordinary Life Operators")
        group.permissions.add(permission)
        viewer.groups.add(group)
        created = OrdinaryLifeOperationsService.create_document(
            proposal=self.proposal,
            document_type="PASSPORT",
            actor=viewer,
        )
        self.assertEqual(created.status, "PENDING")

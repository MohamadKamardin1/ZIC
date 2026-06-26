import uuid
from datetime import date, timedelta
from decimal import Decimal

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.users.models import User
from apps.partners.models import (
    Partner, PartnerType, PartnerTypeAssignment,
    PartnerDocument, PartnerTypeDocumentRequirement,
    PartnerKYCProfile, PartnerDynamicFieldValue,
    DocumentVersion, KYCReviewHistory,
    PartnerTypeAssignmentHistory,
)
from apps.governance.models import (
    AuditLog, ApprovalRequest, ConfigurationVersion,
)
from apps.governance.services.audit_service import AuditService, AuditContext
from apps.governance.services.approval_service import ApprovalService

# =============================================================================
# Helpers
# =============================================================================


def create_admin(**kwargs):
    defaults = {
        "email": "admin@test.com",
        "username": "admin",
        "password": "Test123!",
        "is_superuser": True,
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def create_user(**kwargs):
    defaults = {
        "email": "user@test.com",
        "username": "user",
        "password": "Test123!",
    }
    defaults.update(kwargs)
    return User.objects.create_user(**defaults)


def create_partner(**overrides):
    defaults = {
        "partner_number": "PN-999999",
        "partner_type": "INDIVIDUAL",
        "first_name": "Jane",
        "surname": "Test",
        "email": "jane@test.com",
        "mobile_number": "+255711000000",
    }
    defaults.update(overrides)
    return Partner.objects.create(**defaults)


def create_partner_type(**overrides):
    defaults = {
        "code": "BROKER",
        "name": "Broker",
    }
    defaults.update(overrides)
    return PartnerType.objects.create(**defaults)


def create_assignment(partner=None, partner_type=None):
    if not partner:
        partner = create_partner()
    if not partner_type:
        partner_type = create_partner_type()
    return PartnerTypeAssignment.objects.create(
        partner=partner,
        partner_type=partner_type,
    )


# =============================================================================
# AuditLog & AuditService Tests
# =============================================================================


class AuditLogModelTest(TestCase):
    def test_create_audit_log(self):
        entry = AuditLog.objects.create(
            action_type="CREATE",
            entity_type="Partner",
            entity_id=uuid.uuid4(),
            entity_repr="PN-000001",
            description="Test entry",
        )
        self.assertEqual(str(entry), "CREATE on Partner (PN-000001)")
        self.assertEqual(entry.action_type, "CREATE")
        self.assertIsNotNone(entry.timestamp)

    def test_audit_log_ordering(self):
        e1 = AuditLog.objects.create(
            action_type="CREATE", entity_type="Test", entity_id=uuid.uuid4(),
        )
        e2 = AuditLog.objects.create(
            action_type="UPDATE", entity_type="Test", entity_id=uuid.uuid4(),
        )
        qs = AuditLog.objects.all()
        self.assertEqual(qs.first(), e2)

    def test_audit_log_indexes(self):
        e1 = AuditLog.objects.create(
            action_type="CREATE", entity_type="Partner", entity_id=uuid.uuid4(),
        )
        fetched = AuditLog.objects.filter(entity_type="Partner", entity_id=e1.entity_id).first()
        self.assertEqual(fetched.pk, e1.pk)


class AuditServiceTest(TestCase):
    def setUp(self):
        self.admin = create_admin()
        self.partner = create_partner()

    def test_log_creates_entry(self):
        entry = AuditService.log(
            action_type="UPDATE",
            entity_type="Partner",
            entity_id=self.partner.pk,
            entity_repr=self.partner.partner_number,
            description="Test audit",
        )
        self.assertIsNotNone(entry)
        self.assertEqual(entry.action_type, "UPDATE")
        self.assertEqual(entry.entity_id, self.partner.pk)

    def test_log_model_action(self):
        entry = AuditService.log_model_action(
            action="CREATE",
            instance=self.partner,
            after_state={"status": "ACTIVE"},
        )
        self.assertEqual(entry.action_type, "CREATE")
        self.assertEqual(entry.entity_type, "partner")

    def test_log_with_context(self):
        AuditContext.set_request(type("Req", (), {
            "user": self.admin,
            "META": {"HTTP_USER_AGENT": "test-agent", "REMOTE_ADDR": "127.0.0.1"},
            "request_id": "req-test123",
        })())
        entry = AuditService.log(
            action_type="LOGIN",
            entity_type="User",
            entity_id=self.admin.pk,
        )
        self.assertEqual(entry.user, self.admin)
        self.assertEqual(entry.ip_address, "127.0.0.1")
        self.assertEqual(entry.user_agent, "test-agent")
        self.assertEqual(entry.request_id, "req-test123")
        AuditContext.clear()

    def test_log_anonymous_user(self):
        AuditContext.set_request(type("Req", (), {
            "user": type("Anon", (), {"is_anonymous": True})(),
            "META": {},
            "request_id": "",
        })())
        entry = AuditService.log(
            action_type="CREATE",
            entity_type="Test",
            entity_id=uuid.uuid4(),
        )
        self.assertIsNone(entry.user)
        AuditContext.clear()


# =============================================================================
# ApprovalRequest & ApprovalService Tests
# =============================================================================


class ApprovalRequestModelTest(TestCase):
    def test_create_approval(self):
        req = ApprovalRequest.objects.create(
            module="partners",
            entity_type="Partner",
            entity_id=uuid.uuid4(),
            action="ASSIGN",
            status="PENDING",
        )
        self.assertEqual(str(req), "ASSIGN on Partner (PENDING)")
        self.assertEqual(req.status, "PENDING")

    def test_approval_status_choices(self):
        for status in ["PENDING", "APPROVED", "REJECTED", "CANCELLED"]:
            req = ApprovalRequest.objects.create(
                module="test", entity_type="Test",
                entity_id=uuid.uuid4(), action="TEST", status=status,
            )
            self.assertEqual(req.status, status)


class ApprovalServiceTest(TestCase):
    def setUp(self):
        self.admin = create_admin()
        self.user = create_user()

    def test_submit_creates_pending(self):
        approval = ApprovalService.submit(
            module="partners",
            entity_type="Partner",
            entity_id=uuid.uuid4(),
            action="ASSIGN",
            submitted_by=self.user,
            requested_data={"partner_type": "BROKER"},
        )
        self.assertEqual(approval.status, "PENDING")
        self.assertEqual(approval.submitted_by, self.user)
        self.assertIn("BROKER", str(approval.requested_data))

    def test_approve_changes_status(self):
        approval = ApprovalService.submit(
            module="partners", entity_type="Test",
            entity_id=uuid.uuid4(), action="TEST",
            submitted_by=self.user,
        )
        approved = ApprovalService.approve(approval.pk, self.admin)
        self.assertEqual(approved.status, "APPROVED")
        self.assertEqual(approved.reviewed_by, self.admin)
        self.assertIsNotNone(approved.reviewed_at)

    def test_approve_rejects_already_approved(self):
        approval = ApprovalService.submit(
            module="partners", entity_type="Test",
            entity_id=uuid.uuid4(), action="TEST",
            submitted_by=self.user,
        )
        ApprovalService.approve(approval.pk, self.admin)
        with self.assertRaises(ValueError):
            ApprovalService.approve(approval.pk, self.admin)

    def test_reject_changes_status(self):
        approval = ApprovalService.submit(
            module="partners", entity_type="Test",
            entity_id=uuid.uuid4(), action="TEST",
            submitted_by=self.user,
        )
        rejected = ApprovalService.reject(approval.pk, self.admin, "Not valid")
        self.assertEqual(rejected.status, "REJECTED")
        self.assertEqual(rejected.comments, "Not valid")

    def test_cancel_changes_status(self):
        approval = ApprovalService.submit(
            module="partners", entity_type="Test",
            entity_id=uuid.uuid4(), action="TEST",
            submitted_by=self.user,
        )
        cancelled = ApprovalService.cancel(approval.pk, self.user)
        self.assertEqual(cancelled.status, "CANCELLED")

    def test_get_pending(self):
        a1 = ApprovalService.submit(
            module="partners", entity_type="Test",
            entity_id=uuid.uuid4(), action="TEST",
            submitted_by=self.user,
        )
        ApprovalService.submit(
            module="other", entity_type="Test",
            entity_id=uuid.uuid4(), action="TEST",
            submitted_by=self.user,
        )
        pending = ApprovalService.get_pending(module="partners")
        self.assertEqual(pending.count(), 1)
        self.assertEqual(pending.first().pk, a1.pk)


# =============================================================================
# ConfigurationVersion Tests
# =============================================================================


class ConfigurationVersionTest(TestCase):
    def setUp(self):
        self.admin = create_admin()

    def test_create_version(self):
        version = ConfigurationVersion.objects.create(
            module="partners",
            version_number=1,
            effective_from=date.today(),
            status="DRAFT",
            created_by=self.admin,
            change_summary="Initial config",
        )
        self.assertEqual(str(version), "partners v1 (DRAFT)")
        self.assertEqual(version.status, "DRAFT")

    def test_unique_version_per_module(self):
        ConfigurationVersion.objects.create(
            module="partners", version_number=1,
            effective_from=date.today(),
        )
        with self.assertRaises(Exception):
            ConfigurationVersion.objects.create(
                module="partners", version_number=1,
                effective_from=date.today(),
            )


# =============================================================================
# DocumentVersion Tests
# =============================================================================


class DocumentVersionTest(TestCase):
    def setUp(self):
        self.admin = create_admin()
        self.partner = create_partner()
        pt = create_partner_type()
        self.assignment = create_assignment(self.partner, pt)
        doc_req = PartnerTypeDocumentRequirement.objects.create(
            partner_type=pt, code="LICENSE", description="License",
        )
        self.document = PartnerDocument.objects.create(
            assignment=self.assignment,
            document_requirement=doc_req,
            status="UPLOADED",
        )

    def test_create_version(self):
        version = DocumentVersion.objects.create(
            document=self.document,
            version_number=1,
            file_name="license_v1.pdf",
            uploaded_by=self.admin,
        )
        self.assertEqual(str(version), f"{self.document} v1")
        self.assertEqual(version.version_number, 1)

    def test_unique_version_per_document(self):
        DocumentVersion.objects.create(
            document=self.document, version_number=1,
        )
        with self.assertRaises(Exception):
            DocumentVersion.objects.create(
                document=self.document, version_number=1,
            )


# =============================================================================
# KYCReviewHistory Tests
# =============================================================================


class KYCReviewHistoryTest(TestCase):
    def setUp(self):
        self.admin = create_admin()
        partner = create_partner()
        pt = create_partner_type()
        self.assignment = create_assignment(partner, pt)
        self.kyc = PartnerKYCProfile.objects.create(
            assignment=self.assignment,
            kyc_status="NOT_SET",
        )

    def test_create_review(self):
        review = KYCReviewHistory.objects.create(
            kyc_profile=self.kyc,
            review_type="INITIAL",
            previous_kyc_status="NOT_SET",
            new_kyc_status="CLEARED",
            new_risk_score=Decimal("25.00"),
            new_risk_level="LOW",
            reviewed_by=self.admin,
            comments="All documents verified.",
        )
        self.assertIn("KYC Review", str(review))
        self.assertEqual(review.review_type, "INITIAL")
        self.assertEqual(review.new_kyc_status, "CLEARED")
        self.assertEqual(review.new_risk_level, "LOW")


# =============================================================================
# PartnerTypeAssignmentHistory Tests
# =============================================================================


class PartnerTypeAssignmentHistoryTest(TestCase):
    def setUp(self):
        self.admin = create_admin()
        partner = create_partner()
        pt = create_partner_type()
        self.assignment = create_assignment(partner, pt)

    def test_create_history(self):
        history = PartnerTypeAssignmentHistory.objects.create(
            assignment=self.assignment,
            previous_status="ACTIVE",
            new_status="INACTIVE",
            reason="Suspended",
            changed_by=self.admin,
        )
        self.assertIn("ACTIVE -> INACTIVE", str(history))
        self.assertEqual(history.new_status, "INACTIVE")
        self.assertEqual(history.changed_by, self.admin)

    def test_status_change_tracked(self):
        self.assignment.status = "INACTIVE"
        self.assignment.save()
        PartnerTypeAssignmentHistory.objects.create(
            assignment=self.assignment,
            previous_status="ACTIVE",
            new_status="INACTIVE",
            reason="Deactivated",
            changed_by=self.admin,
        )
        history = PartnerTypeAssignmentHistory.objects.filter(
            assignment=self.assignment,
        )
        self.assertEqual(history.count(), 1)
        self.assertEqual(history.first().new_status, "INACTIVE")


# =============================================================================
# Audit Log from Partner Activate/Deactivate (View Integration)
# =============================================================================


class PartnerAuditIntegrationTest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin()
        self.client.force_authenticate(user=self.admin)
        self.partner = create_partner(status="ACTIVE")

    def test_deactivate_creates_audit_log(self):
        url = reverse("v1:partners-deactivate", args=[self.partner.id])
        self.client.post(url, {"reason": "Test"}, format="json")
        log = AuditLog.objects.filter(
            entity_type="Partner",
            entity_id=self.partner.pk,
            action_type="DEACTIVATE",
        ).first()
        self.assertIsNotNone(log)
        self.assertIn("Test", log.description)

    def test_activate_creates_audit_log(self):
        self.partner.status = "INACTIVE"
        self.partner.save()
        url = reverse("v1:partners-activate", args=[self.partner.id])
        self.client.post(url, format="json")
        log = AuditLog.objects.filter(
            entity_type="Partner",
            entity_id=self.partner.pk,
            action_type="ACTIVATE",
        ).first()
        self.assertIsNotNone(log)


# =============================================================================
# Governance API Endpoint Tests
# =============================================================================


class GovernanceAPITest(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = create_admin()
        self.client.force_authenticate(user=self.admin)
        AuditLog.objects.create(
            action_type="CREATE", entity_type="Partner",
            entity_id=uuid.uuid4(), entity_repr="PN-001",
        )

    def test_audit_log_list(self):
        url = reverse("v1:audit-logs-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("data", response.data)
        self.assertIn("pagination", response.data)

    def test_audit_log_retrieve(self):
        log = AuditLog.objects.first()
        url = reverse("v1:audit-logs-detail", args=[log.pk])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_audit_log_actions(self):
        url = reverse("v1:audit-logs-actions")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.data.get("data"), list)

    def test_audit_log_stats(self):
        url = reverse("v1:audit-logs-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("total", response.data.get("data", {}))

    def test_audit_log_filter_by_entity_type(self):
        url = reverse("v1:audit-logs-list") + "?entity_type=Partner"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_approval_create(self):
        url = reverse("v1:approvals-list")
        data = {
            "module": "partners",
            "entity_type": "Partner",
            "entity_id": str(uuid.uuid4()),
            "action": "UPDATE",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["data"]["status"], "PENDING")

    def test_approval_approve(self):
        approval = ApprovalService.submit(
            module="test", entity_type="Test",
            entity_id=uuid.uuid4(), action="TEST",
            submitted_by=self.admin,
        )
        url = reverse("v1:approvals-approve", args=[approval.pk])
        response = self.client.post(url, {"comments": "OK"}, format="json")
        self.assertEqual(response.status_code, 200)
        approval.refresh_from_db()
        self.assertEqual(approval.status, "APPROVED")

    def test_approval_reject(self):
        approval = ApprovalService.submit(
            module="test", entity_type="Test",
            entity_id=uuid.uuid4(), action="TEST",
            submitted_by=self.admin,
        )
        url = reverse("v1:approvals-reject", args=[approval.pk])
        response = self.client.post(url, {"comments": "No"}, format="json")
        self.assertEqual(response.status_code, 200)
        approval.refresh_from_db()
        self.assertEqual(approval.status, "REJECTED")

    def test_approval_cancel(self):
        approval = ApprovalService.submit(
            module="test", entity_type="Test",
            entity_id=uuid.uuid4(), action="TEST",
            submitted_by=self.admin,
        )
        url = reverse("v1:approvals-cancel", args=[approval.pk])
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        approval.refresh_from_db()
        self.assertEqual(approval.status, "CANCELLED")

    def test_approval_stats(self):
        url = reverse("v1:approvals-stats")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("total", response.data.get("data", {}))

    def test_approval_pending_filter(self):
        ApprovalService.submit(
            module="partners", entity_type="Partner",
            entity_id=uuid.uuid4(), action="UPDATE",
            submitted_by=self.admin,
        )
        url = reverse("v1:approvals-pending") + "?module=partners"
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        data = response.data.get("data", response.data.get("results", []))
        self.assertGreaterEqual(len(data), 1)

    def test_config_version_create(self):
        url = reverse("v1:config-versions-list")
        data = {
            "module": "partners",
            "effective_from": str(date.today()),
            "change_summary": "v1 config",
            "status": "DRAFT",
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(response.status_code, 201)
        if isinstance(response.data, dict) and "version_number" in response.data:
            version_number = response.data["version_number"]
        elif isinstance(response.data, dict) and "data" in response.data:
            version_number = response.data["data"].get("version_number")
        else:
            version_number = None
        self.assertEqual(version_number, 1)

    def test_config_version_activate(self):
        version = ConfigurationVersion.objects.create(
            module="partners", version_number=1,
            effective_from=date.today(), status="DRAFT",
            created_by=self.admin,
        )
        url = reverse("v1:config-versions-activate", args=[version.pk])
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        version.refresh_from_db()
        self.assertEqual(version.status, "ACTIVE")

    def test_config_version_retire(self):
        version = ConfigurationVersion.objects.create(
            module="partners", version_number=1,
            effective_from=date.today(), status="ACTIVE",
            created_by=self.admin,
        )
        url = reverse("v1:config-versions-retire", args=[version.pk])
        response = self.client.post(url, format="json")
        self.assertEqual(response.status_code, 200)
        version.refresh_from_db()
        self.assertEqual(version.status, "RETIRED")

    def test_config_version_active_filter(self):
        ConfigurationVersion.objects.create(
            module="partners", version_number=1,
            effective_from=date.today(), status="ACTIVE",
        )
        url = reverse("v1:config-versions-active")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_compliance_overview(self):
        url = reverse("v1:compliance-overview")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertIn("total_partners", response.data.get("data", {}))

    def test_compliance_expiring_documents(self):
        url = reverse("v1:compliance-expiring-documents")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_compliance_high_risk(self):
        url = reverse("v1:compliance-high-risk-partners")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_unauthenticated_access_blocked(self):
        self.client.force_authenticate(user=None)
        url = reverse("v1:audit-logs-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 401)

    def test_non_admin_cannot_list_audit_logs(self):
        user = create_user()
        self.client.force_authenticate(user=user)
        url = reverse("v1:audit-logs-list")
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

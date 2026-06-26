import logging

from celery import shared_task
from django.utils import timezone
from django.db.models import Q

logger = logging.getLogger(__name__)


@shared_task
def monitor_expired_documents():
    from apps.partners.models import PartnerDocument
    today = timezone.now().date()
    expired = PartnerDocument.objects.filter(
        Q(status="APPROVED") | Q(status="UPLOADED"),
        expiry_date__lt=today,
    )
    count = expired.count()
    if count:
        expired.update(status="EXPIRED")
        logger.warning("Auto-expired %s documents.", count)
    return f"Expired {count} documents."


@shared_task
def monitor_pending_kyc():
    from apps.partners.models import PartnerKYCProfile
    pending = PartnerKYCProfile.objects.filter(kyc_status="NOT_SET")
    count = pending.count()
    logger.info("Pending KYC reviews: %s", count)
    return f"Pending KYC: {count}"


@shared_task
def monitor_high_risk_partners():
    from apps.partners.models import PartnerKYCProfile
    high_risk = PartnerKYCProfile.objects.filter(risk_level__in=["HIGH", "CRITICAL"])
    count = high_risk.count()
    logger.warning("High risk partners: %s", count)
    return f"High risk: {count}"


@shared_task
def monitor_pending_approvals():
    from apps.governance.models import ApprovalRequest
    pending = ApprovalRequest.objects.filter(status="PENDING")
    count = pending.count()
    logger.info("Pending approvals: %s", count)
    return f"Pending approvals: {count}"


@shared_task
def monitor_failed_workflow_transitions():
    from apps.governance.models import AuditLog
    from django.utils import timezone
    since = timezone.now() - timezone.timedelta(hours=24)
    failed = AuditLog.objects.filter(
        action_type="REJECT",
        created_at__gte=since,
    ).count()
    if failed:
        logger.warning("Rejected operations in last 24h: %s", failed)
    return f"Rejections in 24h: {failed}"


@shared_task
def generate_compliance_report():
    from apps.partners.models import (
        Partner, PartnerKYCProfile, PartnerDocument, PartnerTypeAssignment,
    )
    today = timezone.now().date()
    return {
        "total_partners": Partner.objects.count(),
        "active_partners": Partner.objects.filter(status="ACTIVE").count(),
        "kyc_pending": PartnerKYCProfile.objects.filter(kyc_status="NOT_SET").count(),
        "kyc_cleared": PartnerKYCProfile.objects.filter(kyc_status="CLEARED").count(),
        "kyc_rejected": PartnerKYCProfile.objects.filter(kyc_status="REJECTED").count(),
        "kyc_escalated": PartnerKYCProfile.objects.filter(kyc_status="ESCALATED").count(),
        "high_risk": PartnerKYCProfile.objects.filter(risk_level__in=["HIGH", "CRITICAL"]).count(),
        "expired_documents": PartnerDocument.objects.filter(
            status="EXPIRED",
        ).count(),
        "expiring_30_days": PartnerDocument.objects.filter(
            status="APPROVED",
            expiry_date__lte=today + timezone.timedelta(days=30),
            expiry_date__gte=today,
        ).count(),
    }

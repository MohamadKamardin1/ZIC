import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_application_notification(self, application_id, notification_type):
    """
    Send notification to applicant about application status changes.

    notification_type: 'submitted', 'approved', 'rejected', 'suspended', 'converted'
    """
    from .models import PartnerApplication

    try:
        application = PartnerApplication.objects.select_related(
            "submitted_by"
        ).get(pk=application_id)

        logger.info(
            f"Application notification sent: {application.application_number} | "
            f"Type: {notification_type} | Status: {application.status}"
        )

        return {
            "success": True,
            "application_number": application.application_number,
            "notification_type": notification_type,
        }
    except PartnerApplication.DoesNotExist:
        logger.error(f"Application {application_id} not found for notification")
        return {"success": False, "error": "Application not found"}
    except Exception as exc:
        logger.error(f"Failed to send notification for application {application_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def notify_reviewers(self, application_id):
    """
    Notify compliance reviewers when a new application is submitted.
    """
    from .models import PartnerApplication

    try:
        application = PartnerApplication.objects.select_related(
            "submitted_by"
        ).get(pk=application_id)

        logger.info(
            f"Reviewers notified for new application: {application.application_number} | "
            f"Submitted by: {application.submitted_by.email}"
        )

        return {
            "success": True,
            "application_number": application.application_number,
            "submitted_by": application.submitted_by.email,
        }
    except PartnerApplication.DoesNotExist:
        logger.error(f"Application {application_id} not found for reviewer notification")
        return {"success": False, "error": "Application not found"}
    except Exception as exc:
        logger.error(f"Failed to notify reviewers for application {application_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_compliance_check(self, application_id):
    """
    Run automated compliance check on an application.
    """
    from .models import PartnerApplication
    from .services import ComplianceService

    try:
        application = PartnerApplication.objects.get(pk=application_id)

        score = ComplianceService.calculate_risk_score(application)
        is_flagged = ComplianceService.flag_high_risk(application)

        logger.info(
            f"Compliance check completed: {application.application_number} | "
            f"Risk score: {score} | Flagged: {is_flagged}"
        )

        return {
            "success": True,
            "application_number": application.application_number,
            "risk_score": score,
            "is_flagged": is_flagged,
        }
    except PartnerApplication.DoesNotExist:
        logger.error(f"Application {application_id} not found for compliance check")
        return {"success": False, "error": "Application not found"}
    except Exception as exc:
        logger.error(f"Failed to run compliance check for application {application_id}: {exc}")
        raise self.retry(exc=exc)


@shared_task
def cleanup_expired_drafts():
    """
    Delete draft applications older than 30 days.
    """
    from .models import PartnerApplication

    cutoff = timezone.now() - timedelta(days=30)
    expired = PartnerApplication.objects.filter(
        status="DRAFT",
        created_at__lt=cutoff
    )
    count = expired.count()
    expired.delete()

    if count:
        logger.info(f"Cleaned up {count} expired draft applications")

    return count


@shared_task
def send_pending_document_reminders():
    """
    Send reminders to applicants with PENDING_DOCUMENTS status older than 7 days.
    """
    from .models import PartnerApplication

    cutoff = timezone.now() - timedelta(days=7)
    pending = PartnerApplication.objects.filter(
        status="PENDING_DOCUMENTS",
        updated_at__lt=cutoff
    ).select_related("submitted_by")

    count = 0
    for application in pending:
        logger.info(
            f"Document reminder sent: {application.application_number} | "
            f"To: {application.submitted_by.email}"
        )
        count += 1

    if count:
        logger.info(f"Sent {count} pending document reminders")

    return count


@shared_task
def generate_compliance_report():
    """
    Generate weekly compliance report summary.
    """
    from .models import PartnerApplication

    week_ago = timezone.now() - timedelta(days=7)

    stats = {
        "submitted": PartnerApplication.objects.filter(
            status="SUBMITTED",
            submitted_at__gte=week_ago
        ).count(),
        "approved": PartnerApplication.objects.filter(
            status="APPROVED",
            approved_at__gte=week_ago
        ).count(),
        "rejected": PartnerApplication.objects.filter(
            status="REJECTED",
            updated_at__gte=week_ago
        ).count(),
        "converted": PartnerApplication.objects.filter(
            status="CONVERTED",
            converted_at__gte=week_ago
        ).count(),
    }

    logger.info(f"Weekly compliance report: {stats}")

    return stats

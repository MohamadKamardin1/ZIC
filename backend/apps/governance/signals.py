from django.dispatch import Signal, receiver

# Signal emitted when approval status changes
approval_status_changed = Signal()


@receiver(approval_status_changed)
def handle_partner_approval(sender, approval_request, **kwargs):
    """Handle partner application approval status changes"""
    if approval_request.entity_type != 'partner_application':
        return
    
    try:
        from apps.partner_onboarding.models import PartnerApplication
        from apps.partner_onboarding.services.application_service import ApplicationService
        
        application = PartnerApplication.objects.get(id=approval_request.entity_id)
        service = ApplicationService()
        
        if approval_request.status == 'APPROVED':
            service.approve(application, approved_by=approval_request.approved_by)
        elif approval_request.status == 'REJECTED':
            service.reject(application, reason=approval_request.comments, rejected_by=approval_request.approved_by)
    except PartnerApplication.DoesNotExist:
        pass

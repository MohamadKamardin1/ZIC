from django.contrib import admin
from django.utils.html import format_html
from .models import PartnerApplication, PartnerApplicationDocument, PartnerApplicationTask


class PartnerApplicationDocumentInline(admin.TabularInline):
    """Inline for partner application documents."""
    model = PartnerApplicationDocument
    extra = 0
    readonly_fields = ('created_at', 'file_size_display', 'is_verified', 'verified_by', 'verified_at')
    fields = ('document_type', 'document_name', 'file', 'file_size_display', 'created_at', 'is_verified', 'verified_by', 'verified_at')

    def file_size_display(self, obj):
        if obj.file_size:
            size_mb = obj.file_size / (1024 * 1024)
            return f"{size_mb:.2f} MB"
        return "-"
    file_size_display.short_description = "File Size"


class PartnerApplicationTaskInline(admin.TabularInline):
    """Inline for partner application tasks."""
    model = PartnerApplicationTask
    extra = 0
    readonly_fields = ('created_at', 'completed_at', 'completed_by')
    fields = ('task_type', 'description', 'assigned_to', 'status', 'due_date', 'created_at', 'completed_at', 'completed_by')


@admin.register(PartnerApplication)
class PartnerApplicationAdmin(admin.ModelAdmin):
    """Admin configuration for PartnerApplication model."""

    list_display = (
        'application_number',
        'partner_type',
        'applicant_name',
        'email',
        'mobile_number',
        'status_badge',
        'political_risk',
        'aml_risk',
        'submitted_at',
        'created_at',
    )

    list_filter = (
        'status',
        'partner_type',
        'political_risk',
        'aml_risk',
        'created_at',
        'submitted_at',
    )

    search_fields = (
        'application_number',
        'first_name',
        'surname',
        'company_name',
        'email',
        'mobile_number',
        'identification_number',
        'tin_number',
    )

    readonly_fields = (
        'application_number',
        'status',
        'submitted_at',
        'reviewed_at',
        'approved_at',
        'converted_at',
        'created_at',
        'updated_at',
        'submitted_by',
        'reviewed_by',
        'approved_by',
        'partner_record',
    )

    fieldsets = (
        ('Application Information', {
            'fields': ('application_number', 'partner_type', 'status'),
            'classes': ('wide',),
        }),
        ('Individual Partner Details', {
            'fields': (
                'first_name',
                'other_name',
                'surname',
                'gender',
                'date_of_birth',
                'nationality',
                'marital_status',
                'identification_type',
                'identification_number',
            ),
            'classes': ('collapse', 'wide'),
        }),
        ('Corporate Partner Details', {
            'fields': (
                'company_name',
                'tin_number',
                'incorporation_date',
                'industry',
            ),
            'classes': ('collapse', 'wide'),
        }),
        ('Contact Information', {
            'fields': (
                'email',
                'mobile_number',
                'telephone_number',
                'physical_address',
                'postal_address',
                'contact_person',
                'contact_person_phone',
                'contact_person_email',
            ),
            'classes': ('wide',),
        }),
        ('Risk Assessment', {
            'fields': ('political_risk', 'aml_risk'),
            'classes': ('wide',),
        }),
        ('Workflow Information', {
            'fields': (
                'submitted_by',
                'submitted_at',
                'reviewed_by',
                'reviewed_at',
                'approved_by',
                'approved_at',
                'converted_at',
                'partner_record',
            ),
            'classes': ('collapse', 'wide'),
        }),
        ('Notes', {
            'fields': ('rejection_reason', 'compliance_notes'),
            'classes': ('collapse', 'wide'),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    inlines = [PartnerApplicationDocumentInline, PartnerApplicationTaskInline]

    actions = [
        'mark_as_submitted',
        'mark_as_under_review',
        'mark_as_compliance_check',
        'mark_as_approved',
        'mark_as_rejected',
        'mark_as_suspended',
    ]

    def applicant_name(self, obj):
        """Display applicant name based on partner type."""
        if obj.partner_type == 'INDIVIDUAL':
            name_parts = [obj.first_name, obj.other_name, obj.surname]
            return ' '.join(filter(None, name_parts))
        return obj.company_name
    applicant_name.short_description = "Applicant Name"

    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'DRAFT': '#6c757d',
            'SUBMITTED': '#0d6efd',
            'UNDER_REVIEW': '#ffc107',
            'PENDING_DOCUMENTS': '#fd7e14',
            'COMPLIANCE_CHECK': '#6610f2',
            'APPROVED': '#198754',
            'CONVERTED': '#20c997',
            'REJECTED': '#dc3545',
            'SUSPENDED': '#6f42c1',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def partner_record(self, obj):
        """Display link to converted partner record."""
        if obj.status == 'CONVERTED' and obj.converted_partner.exists():
            partner = obj.converted_partner.first()
            from django.urls import reverse
            url = reverse('admin:partners_partner_change', args=[partner.id])
            return format_html('<a href="{}">{}</a>', url, partner.partner_number)
        return "-"
    partner_record.short_description = "Partner Record"

    def mark_as_submitted(self, request, queryset):
        """Action to mark applications as submitted."""
        from .services import ApplicationService
        count = 0
        for app in queryset.filter(status='DRAFT'):
            try:
                ApplicationService.submit(app, request.user)
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} application(s) marked as submitted.")
    mark_as_submitted.short_description = "Mark selected as Submitted"

    def mark_as_under_review(self, request, queryset):
        """Action to mark applications as under review."""
        from .services import ApplicationService
        count = 0
        for app in queryset.filter(status='SUBMITTED'):
            try:
                ApplicationService.start_review(app, request.user)
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} application(s) marked as Under Review.")
    mark_as_under_review.short_description = "Mark selected as Under Review"

    def mark_as_compliance_check(self, request, queryset):
        """Action to mark applications as compliance check."""
        from .services import ApplicationService
        count = 0
        for app in queryset.filter(status__in=['UNDER_REVIEW', 'PENDING_DOCUMENTS']):
            try:
                ApplicationService.send_to_compliance(app, request.user)
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} application(s) marked as Compliance Check.")
    mark_as_compliance_check.short_description = "Mark selected as Compliance Check"

    def mark_as_approved(self, request, queryset):
        """Action to mark applications as approved."""
        from .services import ApplicationService
        count = 0
        for app in queryset.filter(status='COMPLIANCE_CHECK'):
            try:
                ApplicationService.approve(app, request.user)
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} application(s) approved.")
    mark_as_approved.short_description = "Approve selected applications"

    def mark_as_rejected(self, request, queryset):
        """Action to mark applications as rejected."""
        from .services import ApplicationService
        count = 0
        for app in queryset.filter(status__in=['UNDER_REVIEW', 'COMPLIANCE_CHECK', 'PENDING_DOCUMENTS']):
            try:
                ApplicationService.reject(app, request.user, reason="Rejected via admin action")
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} application(s) rejected.")
    mark_as_rejected.short_description = "Reject selected applications"

    def mark_as_suspended(self, request, queryset):
        """Action to mark applications as suspended."""
        from .services import ApplicationService
        count = 0
        for app in queryset.filter(status='COMPLIANCE_CHECK'):
            try:
                ApplicationService.suspend(app, request.user)
                count += 1
            except Exception:
                pass
        self.message_user(request, f"{count} application(s) suspended.")
    mark_as_suspended.short_description = "Suspend selected applications"


@admin.register(PartnerApplicationDocument)
class PartnerApplicationDocumentAdmin(admin.ModelAdmin):
    """Admin configuration for PartnerApplicationDocument model."""

    list_display = (
        'document_name',
        'document_type',
        'application',
        'file_size_mb',
        'is_verified',
        'verified_by',
        'created_at',
    )

    list_filter = (
        'document_type',
        'is_verified',
        'created_at',
    )

    search_fields = (
        'document_name',
        'application__application_number',
        'application__first_name',
        'application__surname',
        'application__company_name',
    )

    readonly_fields = ('created_at', 'file_size', 'mime_type')

    def file_size_mb(self, obj):
        """Display file size in MB."""
        if obj.file_size:
            return f"{obj.file_size / (1024 * 1024):.2f} MB"
        return "-"
    file_size_mb.short_description = "File Size"


@admin.register(PartnerApplicationTask)
class PartnerApplicationTaskAdmin(admin.ModelAdmin):
    """Admin configuration for PartnerApplicationTask model."""

    list_display = (
        'task_type',
        'description',
        'application',
        'assigned_to',
        'status',
        'due_date',
        'created_at',
        'completed_at',
    )

    list_filter = (
        'task_type',
        'status',
        'due_date',
        'created_at',
        'completed_at',
    )

    search_fields = (
        'description',
        'application__application_number',
        'assigned_to__username',
        'assigned_to__email',
    )

    readonly_fields = ('created_at', 'completed_at', 'completed_by')

    fieldsets = (
        ('Task Information', {
            'fields': ('task_type', 'description', 'status'),
            'classes': ('wide',),
        }),
        ('Assignment', {
            'fields': ('application', 'assigned_to', 'due_date'),
            'classes': ('wide',),
        }),
        ('Completion', {
            'fields': ('completed_at', 'completed_by'),
            'classes': ('collapse', 'wide'),
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',),
        }),
    )

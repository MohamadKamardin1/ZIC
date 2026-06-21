from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Partner, PartnerType, PartnerContact, PartnerBankAccount


class PartnerContactInline(admin.TabularInline):
    """Inline for partner contacts."""
    model = PartnerContact
    extra = 0
    fields = ('contact_type', 'first_name', 'surname', 'email', 'mobile_number', 'telephone_number')


class PartnerBankAccountInline(admin.TabularInline):
    """Inline for partner bank accounts."""
    model = PartnerBankAccount
    extra = 0
    fields = ('bank_name', 'account_name', 'account_number', 'swift_code', 'currency')


@admin.register(PartnerType)
class PartnerTypeAdmin(admin.ModelAdmin):
    """Admin configuration for PartnerType model."""
    list_display = ['code', 'name', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['code', 'name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['code']

    fieldsets = (
        ('Type Information', {
            'fields': ('code', 'name', 'description', 'is_active'),
            'classes': ('wide',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    """Admin configuration for Partner model."""

    list_display = [
        'partner_number',
        'partner_type',
        'display_name',
        'email',
        'mobile_number',
        'status_badge',
        'political_risk',
        'aml_risk',
        'source_application',
        'created_at',
    ]

    list_filter = [
        'status',
        'partner_type',
        'political_risk',
        'aml_risk',
        'created_at',
        'activated_at',
        'deactivated_at',
    ]

    search_fields = [
        'partner_number',
        'first_name',
        'middle_name',
        'surname',
        'company_name',
        'email',
        'mobile_number',
        'telephone_number',
        'identification_number',
        'tin_number',
    ]

    readonly_fields = [
        'id',
        'partner_number',
        'status',
        'created_from_application',
        'activated_at',
        'deactivated_at',
        'deactivation_reason',
        'created_at',
        'updated_at',
    ]

    inlines = [PartnerContactInline, PartnerBankAccountInline]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    actions = [
        'activate_partners',
        'deactivate_partners',
    ]

    fieldsets = (
        ('Partner Information', {
            'fields': ('partner_number', 'partner_type', 'status'),
            'classes': ('wide',),
        }),
        ('Individual Partner Details', {
            'fields': (
                'title',
                'first_name',
                'middle_name',
                'surname',
                'gender',
                'date_of_birth',
                'nationality',
                'marital_status',
                'occupation',
                'identification_type',
                'identification_number',
            ),
            'classes': ('collapse', 'wide'),
        }),
        ('Corporate Partner Details', {
            'fields': (
                'company_name',
                'company_registration_number',
                'tin_number',
                'incorporation_date',
                'industry',
                'business_nature',
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
            ),
            'classes': ('wide',),
        }),
        ('Corporate Contact Person', {
            'fields': (
                'contact_person',
                'contact_person_phone',
                'contact_person_email',
            ),
            'classes': ('collapse', 'wide'),
        }),
        ('Risk Assessment', {
            'fields': ('political_risk', 'aml_risk'),
            'classes': ('wide',),
        }),
        ('Source Application', {
            'fields': ('created_from_application',),
            'classes': ('collapse', 'wide'),
        }),
        ('Activation Status', {
            'fields': (
                'activated_at',
                'deactivated_at',
                'deactivation_reason',
            ),
            'classes': ('collapse', 'wide'),
        }),
        ('Timestamps', {
            'fields': ('id', 'created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    def status_badge(self, obj):
        """Display status with color coding."""
        colors = {
            'ACTIVE': '#198754',
            'INACTIVE': '#dc3545',
            'SUSPENDED': '#ffc107',
        }
        color = colors.get(obj.status, '#6c757d')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 11px;">{}</span>',
            color,
            obj.get_status_display()
        )
    status_badge.short_description = "Status"

    def source_application(self, obj):
        """Display link to source application."""
        if obj.created_from_application:
            url = reverse('admin:partner_onboarding_partnerapplication_change', args=[obj.created_from_application.id])
            return format_html('<a href="{}">{}</a>', url, obj.created_from_application.application_number)
        return "-"
    source_application.short_description = "Source Application"

    def activate_partners(self, request, queryset):
        """Action to activate selected partners."""
        from django.utils import timezone
        count = 0
        for partner in queryset.filter(status__in=['INACTIVE', 'SUSPENDED']):
            partner.status = 'ACTIVE'
            partner.activated_at = timezone.now()
            partner.deactivated_at = None
            partner.deactivation_reason = ''
            partner.save(update_fields=['status', 'activated_at', 'deactivated_at', 'deactivation_reason', 'updated_at'])
            count += 1
        self.message_user(request, f"{count} partner(s) activated.")
    activate_partners.short_description = "Activate selected partners"

    def deactivate_partners(self, request, queryset):
        """Action to deactivate selected partners."""
        from django.utils import timezone
        count = 0
        for partner in queryset.filter(status='ACTIVE'):
            partner.status = 'INACTIVE'
            partner.deactivated_at = timezone.now()
            partner.deactivation_reason = 'Deactivated via admin action'
            partner.save(update_fields=['status', 'deactivated_at', 'deactivation_reason', 'updated_at'])
            count += 1
        self.message_user(request, f"{count} partner(s) deactivated.")
    deactivate_partners.short_description = "Deactivate selected partners"

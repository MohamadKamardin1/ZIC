from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import (
    Partner, PartnerType, PartnerContact, PartnerBankAccount,
    IndividualProfile, CorporateProfile, PartnerTypeAssignment,
    PartnerTypeFieldConfiguration,
    PartnerTypeContactRequirement,
    PartnerTypeBankRequirement,
    PartnerDocument,
    PartnerDynamicFieldValue,
    PartnerAssignmentContact,
    PartnerAssignmentBankAccount,
    PartnerKYCProfile,
)


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


class IndividualProfileInline(admin.StackedInline):
    model = IndividualProfile
    extra = 0
    can_delete = False
    fields = (
        'identification_type', 'identification_number',
        'title', 'first_name', 'other_name', 'surname',
        'gender', 'date_of_birth', 'marital_status',
        'occupation', 'nationality',
    )


class CorporateProfileInline(admin.StackedInline):
    model = CorporateProfile
    extra = 0
    can_delete = False
    fields = (
        'company_name', 'tin_number', 'incorporation_date',
        'industry', 'contact_person', 'contact_person_phone',
        'contact_person_email',
    )


class PartnerTypeAssignmentInline(admin.TabularInline):
    model = PartnerTypeAssignment
    extra = 0
    fields = ('partner_type', 'branch', 'location', 'status', 'effective_date')


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
        'partner_category',
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
        'partner_category',
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
        'partner_category',
        'created_from_application',
        'activated_at',
        'deactivated_at',
        'deactivation_reason',
        'created_at',
        'updated_at',
    ]

    inlines = [
        IndividualProfileInline,
        CorporateProfileInline,
        PartnerTypeAssignmentInline,
        PartnerContactInline,
        PartnerBankAccountInline,
    ]
    ordering = ['-created_at']
    date_hierarchy = 'created_at'

    actions = [
        'activate_partners',
        'deactivate_partners',
    ]

    fieldsets = (
        ('Partner Information', {
            'fields': ('partner_number', 'partner_type', 'partner_category', 'status'),
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


class PartnerDocumentInline(admin.TabularInline):
    model = PartnerDocument
    extra = 0
    fields = ('document_requirement', 'document_number', 'status', 'expiry_date')
    readonly_fields = ('document_requirement', 'document_number', 'status')


class PartnerDynamicFieldValueInline(admin.TabularInline):
    model = PartnerDynamicFieldValue
    extra = 0
    fields = ('field_config', 'value_json')
    readonly_fields = ('field_config',)


class PartnerAssignmentContactInline(admin.TabularInline):
    model = PartnerAssignmentContact
    extra = 0
    fields = ('contact_requirement', 'first_name', 'last_name', 'email', 'phone', 'is_primary')
    readonly_fields = ('contact_requirement',)


class PartnerAssignmentBankAccountInline(admin.TabularInline):
    model = PartnerAssignmentBankAccount
    extra = 0
    fields = ('bank_requirement', 'bank_name', 'account_name', 'account_number', 'is_primary')
    readonly_fields = ('bank_requirement',)


class PartnerKYCProfileInline(admin.StackedInline):
    model = PartnerKYCProfile
    extra = 0
    can_delete = False
    fields = ('kyc_status', 'last_review_date', 'risk_score', 'risk_level', 'notes')


@admin.register(PartnerTypeFieldConfiguration)
class PartnerTypeFieldConfigurationAdmin(admin.ModelAdmin):
    list_display = ('field_name', 'field_code', 'field_type', 'partner_type', 'is_required', 'is_active', 'display_order')
    list_filter = ('field_type', 'is_required', 'is_active', 'partner_type')
    search_fields = ('field_name', 'field_code')
    ordering = ('partner_type', 'display_order', 'field_name')


@admin.register(PartnerTypeContactRequirement)
class PartnerTypeContactRequirementAdmin(admin.ModelAdmin):
    list_display = ('contact_type', 'partner_type', 'is_required', 'multiple_allowed', 'is_active', 'display_order')
    list_filter = ('is_required', 'is_active', 'partner_type')
    search_fields = ('contact_type',)
    ordering = ('partner_type', 'display_order', 'contact_type')


@admin.register(PartnerTypeBankRequirement)
class PartnerTypeBankRequirementAdmin(admin.ModelAdmin):
    list_display = ('bank_type', 'partner_type', 'is_required', 'multiple_allowed', 'is_active', 'display_order')
    list_filter = ('is_required', 'is_active', 'partner_type')
    search_fields = ('bank_type',)
    ordering = ('partner_type', 'display_order', 'bank_type')


@admin.register(PartnerDocument)
class PartnerDocumentAdmin(admin.ModelAdmin):
    list_display = ('document_requirement', 'assignment', 'document_number', 'status', 'expiry_date', 'created_at')
    list_filter = ('status',)
    search_fields = ('document_number', 'verification_notes')
    readonly_fields = ('file', 'document_number', 'uploaded_at', 'created_at', 'updated_at')


@admin.register(PartnerDynamicFieldValue)
class PartnerDynamicFieldValueAdmin(admin.ModelAdmin):
    list_display = ('field_config', 'assignment', 'created_at')
    search_fields = ('field_config__field_name', 'field_config__field_code')
    readonly_fields = ('created_at', 'updated_at')


@admin.register(PartnerAssignmentContact)
class PartnerAssignmentContactAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'contact_requirement', 'is_primary', 'assignment')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('is_primary',)


@admin.register(PartnerAssignmentBankAccount)
class PartnerAssignmentBankAccountAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_name', 'account_number', 'bank_requirement', 'is_primary', 'assignment')
    search_fields = ('bank_name', 'account_name', 'account_number')
    list_filter = ('is_primary', 'currency')


@admin.register(PartnerKYCProfile)
class PartnerKYCProfileAdmin(admin.ModelAdmin):
    list_display = ('assignment', 'kyc_status', 'last_review_date', 'risk_score', 'risk_level', 'created_at')
    list_filter = ('kyc_status', 'risk_level')
    search_fields = ('notes',)
    readonly_fields = ('assignment', 'kyc_status', 'risk_score', 'risk_level', 'created_at', 'updated_at')


@admin.register(PartnerTypeAssignment)
class PartnerTypeAssignmentAdmin(admin.ModelAdmin):
    list_display = ('partner', 'partner_type', 'status', 'effective_date', 'created_at')
    list_filter = ('status', 'partner_type')
    search_fields = ('partner__partner_number', 'partner__first_name', 'partner__surname', 'partner__company_name')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [
        PartnerDocumentInline,
        PartnerDynamicFieldValueInline,
        PartnerAssignmentContactInline,
        PartnerAssignmentBankAccountInline,
        PartnerKYCProfileInline,
    ]

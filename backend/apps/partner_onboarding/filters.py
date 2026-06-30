import django_filters
from django.db.models import Q

from apps.partner_onboarding.models import PartnerApplication


class PartnerApplicationFilter(django_filters.FilterSet):
    partner_type = django_filters.ChoiceFilter(choices=[
        ("INDIVIDUAL", "Individual"),
        ("CORPORATE", "Corporate"),
    ])
    status = django_filters.ChoiceFilter(choices=[
        ("DRAFT", "Draft"),
        ("SUBMITTED", "Submitted"),
        ("UNDER_REVIEW", "Under Review"),
        ("PENDING_DOCUMENTS", "Pending Documents"),
        ("COMPLIANCE_CHECK", "Compliance Check"),
        ("APPROVED", "Approved"),
        ("CONVERTED", "Converted to Partner"),
        ("REJECTED", "Rejected"),
        ("SUSPENDED", "Suspended"),
    ])
    political_risk = django_filters.ChoiceFilter(choices=[
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
        ("PEP", "Politically Exposed Person"),
    ])
    aml_risk = django_filters.ChoiceFilter(choices=[
        ("LOW", "Low"),
        ("MEDIUM", "Medium"),
        ("HIGH", "High"),
    ])
    submitted_by = django_filters.UUIDFilter(field_name="submitted_by__id")
    reviewed_by = django_filters.UUIDFilter(field_name="reviewed_by__id")
    approved_by = django_filters.UUIDFilter(field_name="approved_by__id")
    created_from = django_filters.DateFromToRangeFilter(field_name="created_at")
    submitted_from = django_filters.DateFromToRangeFilter(field_name="submitted_at")

    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = PartnerApplication
        fields = [
            "partner_type",
            "status",
            "political_risk",
            "aml_risk",
            "submitted_by",
            "reviewed_by",
            "approved_by",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(application_number__icontains=value)
            | Q(first_name__icontains=value)
            | Q(surname__icontains=value)
            | Q(company_name__icontains=value)
            | Q(email__icontains=value)
            | Q(mobile_number__icontains=value)
        )


class UnifiedOnboardingRecordFilter(django_filters.FilterSet):
    partner_type = django_filters.CharFilter()
    application_status = django_filters.CharFilter()
    kyc_status = django_filters.CharFilter()
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        from apps.partner_onboarding.models import UnifiedOnboardingRecord
        model = UnifiedOnboardingRecord
        fields = [
            "partner_type",
            "application_status",
            "kyc_status",
            "record_type",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(reference_number__icontains=value)
            | Q(display_name__icontains=value)
            | Q(email__icontains=value)
            | Q(mobile_number__icontains=value)
        )


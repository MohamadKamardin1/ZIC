import django_filters
from django.db.models import Q

from apps.partners.models import Partner


class PartnerFilter(django_filters.FilterSet):
    partner_type = django_filters.ChoiceFilter(choices=[
        ("INDIVIDUAL", "Individual"),
        ("CORPORATE", "Corporate"),
        ("AGENT", "Agent"),
        ("BROKER", "Broker"),
    ])
    status = django_filters.ChoiceFilter(choices=[
        ("ACTIVE", "Active"),
        ("INACTIVE", "Inactive"),
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
    created_from = django_filters.DateFromToRangeFilter(field_name="created_at")

    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = Partner
        fields = [
            "partner_type",
            "status",
            "political_risk",
            "aml_risk",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(partner_number__icontains=value)
            | Q(first_name__icontains=value)
            | Q(surname__icontains=value)
            | Q(company_name__icontains=value)
            | Q(email__icontains=value)
            | Q(mobile_number__icontains=value)
        )

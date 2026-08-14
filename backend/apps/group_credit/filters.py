"""
Group Credit — Django Filter FilterSets

Provides rich query filtering for the core transactional endpoints:
quotations, schemes, borrowers (members), claims, and medical cases.
"""

import django_filters
from django.db.models import Q

from apps.group_credit.models import (
    GCQuotation, GCScheme, GCSchemeMember, GCClaim, GCMedicalCase,
)


class GCQuotationFilter(django_filters.FilterSet):
    status = django_filters.CharFilter()
    partner = django_filters.UUIDFilter(field_name="partner__id")
    product = django_filters.UUIDFilter(field_name="product__id")
    scheme_type = django_filters.UUIDFilter(field_name="scheme_type__id")
    date_from = django_filters.DateFilter(field_name="quotation_date", lookup_expr="gte")
    date_to = django_filters.DateFilter(field_name="quotation_date", lookup_expr="lte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = GCQuotation
        fields = ["status", "partner", "product", "scheme_type"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(quotation_number__icontains=value)
            | Q(partner__company_name__icontains=value)
            | Q(partner__partner_number__icontains=value)
            | Q(notes__icontains=value)
        )


class GCSchemeFilter(django_filters.FilterSet):
    status = django_filters.UUIDFilter(field_name="status__id")
    status_code = django_filters.CharFilter(field_name="status__code")
    partner = django_filters.UUIDFilter(field_name="partner__id")
    product = django_filters.UUIDFilter(field_name="product__id")
    scheme_type = django_filters.UUIDFilter(field_name="scheme_type__id")
    expiry_from = django_filters.DateFilter(field_name="expiry_date", lookup_expr="gte")
    expiry_to = django_filters.DateFilter(field_name="expiry_date", lookup_expr="lte")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = GCScheme
        fields = ["status", "status_code", "partner", "product", "scheme_type"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(scheme_number__icontains=value)
            | Q(partner__company_name__icontains=value)
            | Q(partner__partner_number__icontains=value)
            | Q(notes__icontains=value)
        )


class GCSchemeMemberFilter(django_filters.FilterSet):
    scheme = django_filters.UUIDFilter(field_name="scheme__id")
    category = django_filters.UUIDFilter(field_name="category__id")
    status = django_filters.UUIDFilter(field_name="status__id")
    status_code = django_filters.CharFilter(field_name="status__code")
    uw_status = django_filters.CharFilter()
    requires_medical_uw = django_filters.BooleanFilter()
    gender = django_filters.CharFilter()
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = GCSchemeMember
        fields = [
            "scheme", "category", "status", "status_code",
            "uw_status", "requires_medical_uw", "gender",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(member_number__icontains=value)
            | Q(first_name__icontains=value)
            | Q(surname__icontains=value)
            | Q(loan_account_number__icontains=value)
            | Q(identification_number__icontains=value)
            | Q(email__icontains=value)
        )


class GCClaimFilter(django_filters.FilterSet):
    scheme = django_filters.UUIDFilter(field_name="scheme__id")
    member = django_filters.UUIDFilter(field_name="member__id")
    claim_type = django_filters.UUIDFilter(field_name="claim_type__id")
    status = django_filters.UUIDFilter(field_name="status__id")
    status_code = django_filters.CharFilter(field_name="status__code")
    incident_from = django_filters.DateFilter(field_name="incident_date", lookup_expr="gte")
    incident_to = django_filters.DateFilter(field_name="incident_date", lookup_expr="lte")
    reinsurance_notified = django_filters.BooleanFilter()
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = GCClaim
        fields = [
            "scheme", "member", "claim_type", "status", "status_code",
            "reinsurance_notified",
        ]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(claim_number__icontains=value)
            | Q(member__member_number__icontains=value)
            | Q(member__surname__icontains=value)
            | Q(member__first_name__icontains=value)
            | Q(claimant_name__icontains=value)
            | Q(scheme__scheme_number__icontains=value)
        )


class GCMedicalCaseFilter(django_filters.FilterSet):
    member = django_filters.UUIDFilter(field_name="member__id")
    status = django_filters.CharFilter()
    decision = django_filters.UUIDFilter(field_name="decision__id")
    facility = django_filters.UUIDFilter(field_name="facility__id")
    search = django_filters.CharFilter(method="filter_search")

    class Meta:
        model = GCMedicalCase
        fields = ["member", "status", "decision", "facility"]

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(case_number__icontains=value)
            | Q(member__member_number__icontains=value)
            | Q(member__surname__icontains=value)
            | Q(member__first_name__icontains=value)
        )

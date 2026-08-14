"""
Group Credit — REST API Serializers

Organized by architectural layer:
- Setup / Parameter serializers (simple ModelSerializers)
- Quotation serializers (List/Detail/Create with nested categories & riders)
- Scheme serializers (with nested categories, riders, member counts)
- Borrower (Member) serializers (with loan details, FCL flagging, dependents)
- Medical UW serializers (case management with decision workflow)
- Claims serializers (with installments, outstanding balance tracking)
- Renewal serializers
"""

import logging

from rest_framework import serializers

from apps.group_credit.models import (
    GCLookupValue,
    # Layer 1 — Parameters
    GCSchemeType, GCSchemeStatus, GCSchemeMemberStatus, GCSchemeRenewalStatus,
    GCSchemePremiumRate, GCHealthQuestion, GCHealthQuestionnaire,
    # Layer 2 — Products & Riders
    GCSubProduct, GCProduct, GCRider, GCRiderRate,
    # Layer 3 — Quotations
    GCQuotation, GCQuotationCategory, GCQuotationRider,
    # Layer 4 — Schemes & Members
    GCScheme, GCSchemeCategory, GCSchemeRider, GCSchemeMember,
    GCSchemeMemberDependent,
    # Layer 5 — Medical UW
    GCMedicalCode, GCMedicalLimit, GCUnderwritingDecision,
    GCPersonalHabit, GCMedicalHistory, GCMedicalFacility,
    GCMedicalPractitioner, GCMedicalCase,
    # Layer 6 — Claims
    GCClaimType, GCClaimReason, GCClaimStatus, GCDischargeType,
    GCCorrespondentType, GCClaim, GCClaimInstallment, GCMedicalInvoice,
    # Layer 7 — Renewals
    GCSchemeRenewal,
)
from apps.group_credit.services import GCNumberingService

logger = logging.getLogger(__name__)


# =============================================================================
# LAYER 1 — PARAMETER / SETUP SERIALIZERS
# =============================================================================


class GCLookupValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCLookupValue
        fields = "__all__"

class GCSchemeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCSchemeType
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCSchemeStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCSchemeStatus
        fields = [
            "id", "code", "name", "description",
            "sort_order", "is_terminal", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCSchemeMemberStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCSchemeMemberStatus
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCSchemeRenewalStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCSchemeRenewalStatus
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCSchemePremiumRateSerializer(serializers.ModelSerializer):
    rate_type_display = serializers.CharField(source="get_rate_type_display", read_only=True)
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)

    class Meta:
        model = GCSchemePremiumRate
        fields = [
            "id", "name", "rate_type", "rate_type_display",
            "age_band_start", "age_band_end",
            "gender", "gender_display", "occupation_class",
            "rate_per_mille", "flat_rate",
            "effective_date", "expiry_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCHealthQuestionSerializer(serializers.ModelSerializer):
    question_type_display = serializers.CharField(source="get_question_type_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = GCHealthQuestion
        fields = [
            "id", "code", "question_text", "question_type", "question_type_display",
            "category", "category_display", "options",
            "sort_order", "is_required", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCHealthQuestionnaireSerializer(serializers.ModelSerializer):
    questions = GCHealthQuestionSerializer(many=True, read_only=True)
    question_ids = serializers.PrimaryKeyRelatedField(
        queryset=GCHealthQuestion.objects.all(),
        many=True, write_only=True, source="questions", required=False,
    )

    class Meta:
        model = GCHealthQuestionnaire
        fields = [
            "id", "code", "name", "description", "version",
            "questions", "question_ids",
            "effective_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# LAYER 2 — PRODUCT & RIDER SERIALIZERS
# =============================================================================


class GCSubProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCSubProduct
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCRiderRateSerializer(serializers.ModelSerializer):
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)

    class Meta:
        model = GCRiderRate
        fields = [
            "id", "rider", "age_band_start", "age_band_end",
            "gender", "gender_display",
            "rate_per_mille", "flat_amount",
            "effective_date", "expiry_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCRiderSerializer(serializers.ModelSerializer):
    rider_type_display = serializers.CharField(source="get_rider_type_display", read_only=True)
    rates = GCRiderRateSerializer(many=True, read_only=True)

    class Meta:
        model = GCRider
        fields = [
            "id", "code", "name", "description",
            "rider_type", "rider_type_display",
            "is_mandatory", "is_active", "rates",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCProductListSerializer(serializers.ModelSerializer):
    sub_product_name = serializers.ReadOnlyField(source="sub_product.name")

    class Meta:
        model = GCProduct
        fields = [
            "id", "code", "name", "sub_product", "sub_product_name",
            "min_members", "max_members",
            "min_loan_amount", "max_loan_amount",
            "free_cover_limit", "min_entry_age", "max_entry_age", "max_cover_age",
            "currency", "is_active",
            "created_at", "updated_at",
        ]


class GCProductDetailSerializer(serializers.ModelSerializer):
    sub_product = GCSubProductSerializer(read_only=True)
    sub_product_id = serializers.PrimaryKeyRelatedField(
        queryset=GCSubProduct.objects.all(), write_only=True, source="sub_product",
    )

    class Meta:
        model = GCProduct
        fields = [
            "id", "code", "name", "sub_product", "sub_product_id", "description",
            "min_members", "max_members",
            "min_loan_amount", "max_loan_amount",
            "min_entry_age", "max_entry_age", "max_cover_age",
            "free_cover_limit",
            "currency", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# LAYER 3 — QUOTATION SERIALIZERS
# =============================================================================


class GCQuotationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GCQuotationCategory
        fields = [
            "id", "quotation", "category_name", "description",
            "flat_loan_amount",
            "member_count", "total_loan_amount", "annual_premium",
            "premium_rate_per_mille", "sort_order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCQuotationRiderSerializer(serializers.ModelSerializer):
    rider_name = serializers.ReadOnlyField(source="rider.name")
    rider_type = serializers.ReadOnlyField(source="rider.rider_type")

    class Meta:
        model = GCQuotationRider
        fields = [
            "id", "quotation", "rider", "rider_name", "rider_type",
            "rate_per_mille", "total_premium",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCQuotationListSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()
    product_name = serializers.ReadOnlyField(source="product.name")
    scheme_type_name = serializers.ReadOnlyField(source="scheme_type.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    prepared_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GCQuotation
        fields = [
            "id", "quotation_number", "partner", "partner_name",
            "product", "product_name", "scheme_type", "scheme_type_name",
            "status", "status_display",
            "quotation_date", "valid_until",
            "total_members", "total_loan_amount", "total_annual_premium",
            "prepared_by", "prepared_by_name",
            "created_at",
        ]

    def get_partner_name(self, obj):
        if hasattr(obj.partner, 'company_name') and obj.partner.company_name:
            return obj.partner.company_name
        return str(obj.partner)

    def get_prepared_by_name(self, obj):
        if obj.prepared_by:
            return obj.prepared_by.get_full_name() or obj.prepared_by.email
        return None


class GCQuotationDetailSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()
    product_name = serializers.ReadOnlyField(source="product.name")
    product_code = serializers.ReadOnlyField(source="product.code")
    scheme_type_name = serializers.ReadOnlyField(source="scheme_type.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    categories = GCQuotationCategorySerializer(many=True, read_only=True)
    riders = GCQuotationRiderSerializer(many=True, read_only=True)
    prepared_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GCQuotation
        fields = [
            "id", "quotation_number",
            "partner", "partner_name",
            "product", "product_name", "product_code",
            "scheme_type", "scheme_type_name",
            "status", "status_display",
            "quotation_date", "valid_until",
            "total_members", "total_loan_amount", "total_annual_premium",
            "experience_rating_factor", "commission_rate", "admin_loading_rate",
            "free_cover_limit", "notes",
            "categories", "riders",
            "prepared_by", "prepared_by_name",
            "approved_by", "approved_by_name", "approved_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "quotation_number", "created_at", "updated_at",
            "approved_by", "approved_at",
        ]

    def get_partner_name(self, obj):
        if hasattr(obj.partner, 'company_name') and obj.partner.company_name:
            return obj.partner.company_name
        return str(obj.partner)

    def get_prepared_by_name(self, obj):
        if obj.prepared_by:
            return obj.prepared_by.get_full_name() or obj.prepared_by.email
        return None

    def get_approved_by_name(self, obj):
        if obj.approved_by:
            return obj.approved_by.get_full_name() or obj.approved_by.email
        return None


class GCQuotationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCQuotation
        fields = [
            "partner", "product", "scheme_type",
            "quotation_date", "valid_until",
            "total_members", "total_loan_amount", "total_annual_premium",
            "experience_rating_factor", "commission_rate", "admin_loading_rate",
            "free_cover_limit", "notes",
        ]

    def create(self, validated_data):
        validated_data["quotation_number"] = GCNumberingService.generate_quotation_number()
        request = self.context.get("request")
        if request and request.user:
            validated_data["prepared_by"] = request.user
        # Snapshot FCL from product if not explicitly set
        if not validated_data.get("free_cover_limit"):
            validated_data["free_cover_limit"] = validated_data["product"].free_cover_limit
        return super().create(validated_data)


# =============================================================================
# LAYER 4 — SCHEME & BORROWER (MEMBER) SERIALIZERS
# =============================================================================


class GCSchemeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GCSchemeCategory
        fields = [
            "id", "scheme", "category_name", "description",
            "flat_loan_amount",
            "premium_rate_per_mille",
            "min_entry_age", "max_entry_age", "max_cover_age",
            "sort_order", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCSchemeRiderSerializer(serializers.ModelSerializer):
    rider_name = serializers.ReadOnlyField(source="rider.name")
    rider_type = serializers.ReadOnlyField(source="rider.rider_type")

    class Meta:
        model = GCSchemeRider
        fields = [
            "id", "scheme", "rider", "rider_name", "rider_type",
            "rate_per_mille", "flat_amount", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCSchemeListSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()
    product_name = serializers.ReadOnlyField(source="product.name")
    scheme_type_name = serializers.ReadOnlyField(source="scheme_type.name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = GCScheme
        fields = [
            "id", "scheme_number", "partner", "partner_name",
            "product", "product_name", "scheme_type", "scheme_type_name",
            "status", "status_name", "status_code",
            "inception_date", "expiry_date",
            "total_members", "total_sum_assured", "total_annual_premium",
            "currency", "is_expired", "days_until_expiry",
            "created_at",
        ]

    def get_partner_name(self, obj):
        if hasattr(obj.partner, 'company_name') and obj.partner.company_name:
            return obj.partner.company_name
        return str(obj.partner)


class GCSchemeDetailSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()
    product_name = serializers.ReadOnlyField(source="product.name")
    product_code = serializers.ReadOnlyField(source="product.code")
    scheme_type_name = serializers.ReadOnlyField(source="scheme_type.name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    categories = GCSchemeCategorySerializer(many=True, read_only=True)
    riders = GCSchemeRiderSerializer(many=True, read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    converted_from_quotation_number = serializers.ReadOnlyField(
        source="converted_from_quotation.quotation_number"
    )

    class Meta:
        model = GCScheme
        fields = [
            "id", "scheme_number",
            "partner", "partner_name",
            "product", "product_name", "product_code",
            "scheme_type", "scheme_type_name",
            "status", "status_name", "status_code",
            "converted_from_quotation", "converted_from_quotation_number",
            "inception_date", "expiry_date", "renewal_date",
            "free_cover_limit", "experience_rating_factor",
            "commission_rate", "admin_loading_rate",
            "total_members", "total_sum_assured", "total_annual_premium",
            "currency", "policy_document", "notes",
            "categories", "riders",
            "is_expired", "days_until_expiry",
            "created_by", "updated_by",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "scheme_number", "created_at", "updated_at",
        ]

    def get_partner_name(self, obj):
        if hasattr(obj.partner, 'company_name') and obj.partner.company_name:
            return obj.partner.company_name
        return str(obj.partner)


class GCSchemeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCScheme
        fields = [
            "partner", "product", "scheme_type", "status",
            "converted_from_quotation",
            "inception_date", "expiry_date", "renewal_date",
            "free_cover_limit", "experience_rating_factor",
            "commission_rate", "admin_loading_rate",
            "total_members", "total_sum_assured", "total_annual_premium",
            "currency", "notes",
        ]

    def create(self, validated_data):
        validated_data["scheme_number"] = GCNumberingService.generate_scheme_number()
        request = self.context.get("request")
        if request and request.user:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class GCSchemeMemberDependentSerializer(serializers.ModelSerializer):
    relationship_display = serializers.CharField(source="get_relationship_display", read_only=True)

    class Meta:
        model = GCSchemeMemberDependent
        fields = [
            "id", "member", "relationship", "relationship_display",
            "first_name", "surname", "gender", "date_of_birth",
            "sum_assured", "premium_amount",
            "cover_start_date", "cover_end_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCSchemeMemberListSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    category_name = serializers.ReadOnlyField(source="category.category_name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    uw_status_display = serializers.CharField(source="get_uw_status_display", read_only=True)

    class Meta:
        model = GCSchemeMember
        fields = [
            "id", "member_number", "scheme", "scheme_number",
            "category", "category_name",
            "status", "status_name", "status_code",
            "first_name", "surname", "full_name", "gender",
            "date_of_birth", "age",
            "loan_account_number", "loan_amount", "loan_term_months",
            "outstanding_balance",
            "sum_assured", "premium_amount",
            "cover_start_date", "cover_end_date",
            "requires_medical_uw", "uw_status", "uw_status_display",
            "created_at",
        ]


class GCSchemeMemberDetailSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    category_name = serializers.ReadOnlyField(source="category.category_name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    uw_status_display = serializers.CharField(source="get_uw_status_display", read_only=True)
    dependents = GCSchemeMemberDependentSerializer(many=True, read_only=True)

    class Meta:
        model = GCSchemeMember
        fields = [
            "id", "member_number",
            "scheme", "scheme_number",
            "category", "category_name",
            "status", "status_name", "status_code",
            "first_name", "surname", "other_name", "full_name",
            "gender", "date_of_birth", "age",
            "identification_type", "identification_number", "nationality",
            # Loan specifics
            "loan_account_number", "loan_amount", "loan_term_months",
            "interest_rate", "outstanding_balance", "date_of_loan",
            # Cover
            "sum_assured", "premium_amount",
            "cover_start_date", "cover_end_date",
            "requires_medical_uw", "uw_status", "uw_status_display",
            "premium_loading_percent",
            "email", "mobile_number", "physical_address",
            "beneficiary_details", "dependents",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "member_number", "created_at", "updated_at",
            "requires_medical_uw",
        ]


class GCSchemeMemberCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCSchemeMember
        fields = [
            "scheme", "category", "status",
            "first_name", "surname", "other_name",
            "gender", "date_of_birth",
            "identification_type", "identification_number", "nationality",
            # Loan specifics
            "loan_account_number", "loan_amount", "loan_term_months",
            "interest_rate", "outstanding_balance", "date_of_loan",
            # Cover
            "sum_assured", "premium_amount",
            "cover_start_date", "cover_end_date",
            "email", "mobile_number", "physical_address",
            "beneficiary_details",
        ]

    def create(self, validated_data):
        validated_data["member_number"] = GCNumberingService.generate_member_number()

        # Auto-flag FCL — for credit life, sum_assured is typically the loan_amount
        scheme = validated_data.get("scheme")
        sum_assured = validated_data.get("sum_assured", 0)
        # Default sum_assured to loan_amount if not explicitly set
        if not sum_assured and validated_data.get("loan_amount"):
            sum_assured = validated_data["loan_amount"]
            validated_data["sum_assured"] = sum_assured
        # Default outstanding_balance to loan_amount if not set
        if not validated_data.get("outstanding_balance") and validated_data.get("loan_amount"):
            validated_data["outstanding_balance"] = validated_data["loan_amount"]

        if scheme and sum_assured > scheme.free_cover_limit:
            validated_data["requires_medical_uw"] = True
            validated_data["uw_status"] = "PENDING"
        else:
            validated_data["requires_medical_uw"] = False
            validated_data["uw_status"] = "NOT_REQUIRED"

        return super().create(validated_data)


# =============================================================================
# LAYER 5 — MEDICAL UNDERWRITING SERIALIZERS
# =============================================================================


class GCMedicalCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCMedicalCode
        fields = [
            "id", "code", "name", "description", "icd10_code",
            "category", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCMedicalLimitSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")

    class Meta:
        model = GCMedicalLimit
        fields = [
            "id", "product", "product_name",
            "age_from", "age_to",
            "sum_assured_from", "sum_assured_to",
            "required_tests", "description", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCUnderwritingDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCUnderwritingDecision
        fields = [
            "id", "code", "name", "description", "sort_order",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCPersonalHabitSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    risk_level_display = serializers.CharField(source="get_risk_level_display", read_only=True)

    class Meta:
        model = GCPersonalHabit
        fields = [
            "id", "code", "name", "category", "category_display",
            "risk_level", "risk_level_display", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCMedicalHistorySerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    risk_impact_display = serializers.CharField(source="get_risk_impact_display", read_only=True)

    class Meta:
        model = GCMedicalHistory
        fields = [
            "id", "code", "name", "category", "category_display",
            "risk_impact", "risk_impact_display", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCMedicalFacilitySerializer(serializers.ModelSerializer):
    facility_type_display = serializers.CharField(source="get_facility_type_display", read_only=True)

    class Meta:
        model = GCMedicalFacility
        fields = [
            "id", "code", "name", "facility_type", "facility_type_display",
            "address", "city", "region", "phone", "email", "contact_person",
            "is_approved", "approved_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCMedicalPractitionerSerializer(serializers.ModelSerializer):
    facility_name = serializers.ReadOnlyField(source="facility.name")

    class Meta:
        model = GCMedicalPractitioner
        fields = [
            "id", "code", "name", "specialization", "license_number",
            "facility", "facility_name", "phone", "email",
            "is_approved", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCMedicalCaseListSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source="member.full_name")
    member_number = serializers.ReadOnlyField(source="member.member_number")
    facility_name = serializers.ReadOnlyField(source="facility.name")
    decision_name = serializers.ReadOnlyField(source="decision.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = GCMedicalCase
        fields = [
            "id", "case_number", "member", "member_name", "member_number",
            "facility", "facility_name",
            "status", "status_display",
            "decision", "decision_name",
            "examination_date", "premium_loading_percent",
            "created_at",
        ]


class GCMedicalCaseDetailSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source="member.full_name")
    member_number = serializers.ReadOnlyField(source="member.member_number")
    facility_name = serializers.ReadOnlyField(source="facility.name")
    practitioner_name = serializers.ReadOnlyField(source="practitioner.name")
    decision_name = serializers.ReadOnlyField(source="decision.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    diagnosis_codes = GCMedicalCodeSerializer(many=True, read_only=True)
    personal_habits = GCPersonalHabitSerializer(many=True, read_only=True)
    medical_history = GCMedicalHistorySerializer(many=True, read_only=True)
    questionnaire_name = serializers.ReadOnlyField(source="questionnaire.name")
    decided_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GCMedicalCase
        fields = [
            "id", "case_number",
            "member", "member_name", "member_number",
            "facility", "facility_name",
            "practitioner", "practitioner_name",
            "examination_date",
            "diagnosis_codes", "personal_habits", "medical_history",
            "questionnaire", "questionnaire_name", "questionnaire_responses",
            "decision", "decision_name", "decision_notes",
            "premium_loading_percent", "exclusions",
            "decided_by", "decided_by_name", "decided_at",
            "status", "status_display", "medical_report",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "case_number", "created_at", "updated_at",
            "decided_by", "decided_at",
        ]

    def get_decided_by_name(self, obj):
        if obj.decided_by:
            return obj.decided_by.get_full_name() or obj.decided_by.email
        return None


class GCMedicalCaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCMedicalCase
        fields = [
            "member", "facility", "practitioner",
            "examination_date", "questionnaire",
        ]

    def create(self, validated_data):
        validated_data["case_number"] = GCNumberingService.generate_medical_case_number()
        return super().create(validated_data)


# =============================================================================
# LAYER 6 — CLAIMS SERIALIZERS
# =============================================================================


class GCClaimTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCClaimType
        fields = [
            "id", "code", "name", "description",
            "requires_medical_report", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCClaimReasonSerializer(serializers.ModelSerializer):
    claim_type_name = serializers.ReadOnlyField(source="claim_type.name")

    class Meta:
        model = GCClaimReason
        fields = [
            "id", "code", "name", "claim_type", "claim_type_name",
            "description", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCClaimStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCClaimStatus
        fields = [
            "id", "code", "name", "description",
            "sort_order", "is_terminal", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCDischargeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCDischargeType
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCCorrespondentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCCorrespondentType
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCClaimInstallmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = GCClaimInstallment
        fields = [
            "id", "claim", "installment_number",
            "due_date", "amount", "paid_amount",
            "status", "status_display",
            "payment_reference", "payment_date", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GCClaimListSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    member_name = serializers.ReadOnlyField(source="member.full_name")
    member_number = serializers.ReadOnlyField(source="member.member_number")
    claim_type_name = serializers.ReadOnlyField(source="claim_type.name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    outstanding_amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )

    class Meta:
        model = GCClaim
        fields = [
            "id", "claim_number",
            "scheme", "scheme_number",
            "member", "member_name", "member_number",
            "claim_type", "claim_type_name",
            "status", "status_name", "status_code",
            "incident_date", "notification_date",
            "outstanding_balance_at_claim",
            "claim_amount", "approved_amount", "paid_amount", "outstanding_amount",
            "currency", "reinsurance_notified",
            "created_at",
        ]


class GCClaimDetailSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    member_name = serializers.ReadOnlyField(source="member.full_name")
    member_number = serializers.ReadOnlyField(source="member.member_number")
    claim_type_name = serializers.ReadOnlyField(source="claim_type.name")
    claim_reason_name = serializers.ReadOnlyField(source="claim_reason.name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    discharge_type_name = serializers.ReadOnlyField(source="discharge_type.name")
    outstanding_amount = serializers.DecimalField(
        max_digits=18, decimal_places=2, read_only=True
    )
    installments = GCClaimInstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = GCClaim
        fields = [
            "id", "claim_number",
            "scheme", "scheme_number",
            "member", "member_name", "member_number",
            "claim_type", "claim_type_name",
            "claim_reason", "claim_reason_name",
            "status", "status_name", "status_code",
            "incident_date", "notification_date", "registration_date",
            "sum_assured_at_claim", "outstanding_balance_at_claim",
            "claim_amount", "approved_amount",
            "paid_amount", "outstanding_amount", "currency",
            "discharge_type", "discharge_type_name",
            "claimant_name", "claimant_relationship", "claimant_id_number",
            "claimant_phone", "claimant_email",
            "claimant_bank_name", "claimant_bank_account",
            "medical_report", "death_certificate", "supporting_documents",
            "investigation_notes", "assessment_notes", "rejection_reason",
            "reinsurance_notified", "reinsurance_share", "reinsurance_amount",
            "installments",
            "registered_by", "assessed_by", "approved_by", "paid_by",
            "assessed_at", "approved_at", "paid_at", "closed_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "claim_number", "registration_date",
            "created_at", "updated_at",
            "registered_by", "assessed_by", "approved_by", "paid_by",
            "assessed_at", "approved_at", "paid_at", "closed_at",
        ]


class GCClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCClaim
        fields = [
            "scheme", "member", "claim_type", "claim_reason", "status",
            "incident_date", "notification_date",
            "sum_assured_at_claim", "outstanding_balance_at_claim", "claim_amount",
            "claimant_name", "claimant_relationship", "claimant_id_number",
            "claimant_phone", "claimant_email",
            "claimant_bank_name", "claimant_bank_account",
        ]

    def create(self, validated_data):
        validated_data["claim_number"] = GCNumberingService.generate_claim_number()
        request = self.context.get("request")
        if request and request.user:
            validated_data["registered_by"] = request.user
        # Snapshot member's current balances
        member = validated_data.get("member")
        if member:
            if not validated_data.get("sum_assured_at_claim"):
                validated_data["sum_assured_at_claim"] = member.sum_assured
            if not validated_data.get("outstanding_balance_at_claim"):
                validated_data["outstanding_balance_at_claim"] = member.outstanding_balance
            # Default claim amount to outstanding balance for credit life
            if not validated_data.get("claim_amount"):
                validated_data["claim_amount"] = member.outstanding_balance
            # Default claimant to Partner (Bank) name
            if not validated_data.get("claimant_name"):
                scheme = validated_data.get("scheme")
                if scheme and hasattr(scheme.partner, 'company_name'):
                    validated_data["claimant_name"] = scheme.partner.company_name
        return super().create(validated_data)


class GCMedicalInvoiceSerializer(serializers.ModelSerializer):
    facility_name = serializers.ReadOnlyField(source="facility.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = GCMedicalInvoice
        fields = [
            "id", "claim", "member", "invoice_number",
            "facility", "facility_name",
            "invoice_date", "due_date",
            "total_amount", "approved_amount", "paid_amount",
            "currency", "status", "status_display", "notes",
            "reviewed_by", "approved_by",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# LAYER 7 — RENEWAL SERIALIZERS
# =============================================================================


class GCSchemeRenewalListSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    renewal_status_name = serializers.ReadOnlyField(source="renewal_status.name")
    renewal_status_code = serializers.ReadOnlyField(source="renewal_status.code")

    class Meta:
        model = GCSchemeRenewal
        fields = [
            "id", "renewal_number", "scheme", "scheme_number",
            "renewal_status", "renewal_status_name", "renewal_status_code",
            "current_expiry_date", "proposed_renewal_date",
            "previous_premium", "proposed_premium",
            "claims_experience_ratio",
            "created_at",
        ]


class GCSchemeRenewalDetailSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    renewal_status_name = serializers.ReadOnlyField(source="renewal_status.name")

    class Meta:
        model = GCSchemeRenewal
        fields = [
            "id", "renewal_number", "scheme", "scheme_number",
            "renewal_status", "renewal_status_name",
            "current_expiry_date", "proposed_renewal_date",
            "previous_premium", "proposed_premium",
            "previous_experience_factor", "proposed_experience_factor",
            "claims_experience_ratio",
            "terms_document", "notes",
            "initiated_by", "approved_by",
            "initiated_at", "approved_at",
            "created_at", "updated_at",
        ]
        read_only_fields = [
            "id", "renewal_number", "created_at", "updated_at",
            "initiated_by", "approved_by", "initiated_at", "approved_at",
        ]


class GCSchemeRenewalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GCSchemeRenewal
        fields = [
            "scheme", "renewal_status",
            "current_expiry_date", "proposed_renewal_date",
            "previous_premium", "proposed_premium",
            "previous_experience_factor", "proposed_experience_factor",
            "claims_experience_ratio", "notes",
        ]

    def create(self, validated_data):
        validated_data["renewal_number"] = GCNumberingService.generate_renewal_number()
        request = self.context.get("request")
        if request and request.user:
            validated_data["initiated_by"] = request.user
        return super().create(validated_data)

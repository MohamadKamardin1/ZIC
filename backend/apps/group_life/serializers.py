"""
Group Life — REST API Serializers

Organized by architectural layer:
- Setup / Parameter serializers (simple ModelSerializers)
- Quotation serializers (List/Detail/Create with nested categories & riders)
- Scheme serializers (with nested categories, riders, member counts)
- Member serializers (with FCL flagging and dependent management)
- Medical UW serializers (case management with decision workflow)
- Claims serializers (with installments and reinsurance tracking)
- Renewal serializers
"""

import logging

from rest_framework import serializers

from apps.group_life.models import (
    # Layer 1 — Parameters
    GLLookupValue, GLSchemeType, GLSchemeStatus, GLSchemeMemberStatus, GLSchemeRenewalStatus,
    GLSchemePremiumRate, GLHealthQuestion, GLHealthQuestionnaire,
    # Layer 2 — Products & Riders
    GLSubProduct, GLProduct, GLRider, GLRiderRate,
    # Layer 3 — Quotations
    GLQuotation, GLQuotationCategory, GLQuotationRider,
    # Layer 4 — Schemes & Members
    GLScheme, GLSchemeCategory, GLSchemeRider, GLSchemeMember,
    GLSchemeMemberDependent,
    # Layer 5 — Medical UW
    GLMedicalCode, GLMedicalLimit, GLUnderwritingDecision,
    GLPersonalHabit, GLMedicalHistory, GLMedicalFacility,
    GLMedicalPractitioner, GLMedicalCase,
    # Layer 6 — Claims
    GLClaimType, GLClaimReason, GLClaimStatus, GLDischargeType,
    GLCorrespondentType, GLClaim, GLClaimInstallment, GLMedicalInvoice,
    # Layer 7 — Renewals
    GLSchemeRenewal,
)
from apps.group_life.services import GLNumberingService

logger = logging.getLogger(__name__)


# =============================================================================
# LAYER 1 — PARAMETER / SETUP TABLES
# =============================================================================


class GLLookupValueSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLLookupValue
        fields = ["id", "category", "value", "label", "sort_order", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLSchemeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLSchemeType
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLSchemeStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLSchemeStatus
        fields = [
            "id", "code", "name", "description",
            "sort_order", "is_terminal", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLSchemeMemberStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLSchemeMemberStatus
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLSchemeRenewalStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLSchemeRenewalStatus
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLSchemePremiumRateSerializer(serializers.ModelSerializer):
    rate_type_display = serializers.CharField(source="get_rate_type_display", read_only=True)
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)

    class Meta:
        model = GLSchemePremiumRate
        fields = [
            "id", "name", "rate_type", "rate_type_display",
            "age_band_start", "age_band_end",
            "gender", "gender_display", "occupation_class",
            "rate_per_mille", "flat_rate",
            "effective_date", "expiry_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLHealthQuestionSerializer(serializers.ModelSerializer):
    question_type_display = serializers.CharField(source="get_question_type_display", read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = GLHealthQuestion
        fields = [
            "id", "code", "question_text", "question_type", "question_type_display",
            "category", "category_display", "options",
            "sort_order", "is_required", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLHealthQuestionnaireSerializer(serializers.ModelSerializer):
    questions = GLHealthQuestionSerializer(many=True, read_only=True)
    question_ids = serializers.PrimaryKeyRelatedField(
        queryset=GLHealthQuestion.objects.all(),
        many=True, write_only=True, source="questions", required=False,
    )

    class Meta:
        model = GLHealthQuestionnaire
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


class GLSubProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLSubProduct
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLRiderRateSerializer(serializers.ModelSerializer):
    gender_display = serializers.CharField(source="get_gender_display", read_only=True)

    class Meta:
        model = GLRiderRate
        fields = [
            "id", "rider", "age_band_start", "age_band_end",
            "gender", "gender_display",
            "rate_per_mille", "flat_amount",
            "effective_date", "expiry_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLRiderSerializer(serializers.ModelSerializer):
    rider_type_display = serializers.CharField(source="get_rider_type_display", read_only=True)
    rates = GLRiderRateSerializer(many=True, read_only=True)

    class Meta:
        model = GLRider
        fields = [
            "id", "code", "name", "description",
            "rider_type", "rider_type_display",
            "is_mandatory", "is_active", "rates",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLProductListSerializer(serializers.ModelSerializer):
    sub_product_name = serializers.ReadOnlyField(source="sub_product.name")

    class Meta:
        model = GLProduct
        fields = [
            "id", "code", "name", "sub_product", "sub_product_name",
            "min_members", "max_members",
            "free_cover_limit", "min_entry_age", "max_entry_age", "max_cover_age",
            "currency", "is_active",
            "created_at", "updated_at",
        ]


class GLProductDetailSerializer(serializers.ModelSerializer):
    sub_product = GLSubProductSerializer(read_only=True)
    sub_product_id = serializers.PrimaryKeyRelatedField(
        queryset=GLSubProduct.objects.all(), write_only=True, source="sub_product",
    )

    class Meta:
        model = GLProduct
        fields = [
            "id", "code", "name", "sub_product", "sub_product_id", "description",
            "min_members", "max_members",
            "min_sum_assured", "max_sum_assured",
            "min_entry_age", "max_entry_age", "max_cover_age",
            "free_cover_limit",
            "salary_multiple_min", "salary_multiple_max",
            "currency", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# =============================================================================
# LAYER 3 — QUOTATION SERIALIZERS
# =============================================================================


class GLQuotationCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GLQuotationCategory
        fields = [
            "id", "quotation", "category_name", "description",
            "salary_multiple", "flat_sum_assured",
            "member_count", "total_sum_assured", "annual_premium",
            "premium_rate_per_mille", "sort_order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLQuotationRiderSerializer(serializers.ModelSerializer):
    rider_name = serializers.ReadOnlyField(source="rider.name")
    rider_type = serializers.ReadOnlyField(source="rider.rider_type")

    class Meta:
        model = GLQuotationRider
        fields = [
            "id", "quotation", "rider", "rider_name", "rider_type",
            "rate_per_mille", "total_premium",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLQuotationListSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()
    product_name = serializers.ReadOnlyField(source="product.name")
    scheme_type_name = serializers.ReadOnlyField(source="scheme_type.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    prepared_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GLQuotation
        fields = [
            "id", "quotation_number", "partner", "partner_name",
            "product", "product_name", "scheme_type", "scheme_type_name",
            "status", "status_display",
            "quotation_date", "valid_until",
            "total_members", "total_sum_assured", "total_annual_premium",
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


class GLQuotationDetailSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()
    product_name = serializers.ReadOnlyField(source="product.name")
    product_code = serializers.ReadOnlyField(source="product.code")
    scheme_type_name = serializers.ReadOnlyField(source="scheme_type.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    categories = GLQuotationCategorySerializer(many=True, read_only=True)
    riders = GLQuotationRiderSerializer(many=True, read_only=True)
    prepared_by_name = serializers.SerializerMethodField()
    approved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GLQuotation
        fields = [
            "id", "quotation_number",
            "partner", "partner_name",
            "product", "product_name", "product_code",
            "scheme_type", "scheme_type_name",
            "status", "status_display",
            "quotation_date", "valid_until",
            "total_members", "total_sum_assured", "total_annual_premium",
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


class GLQuotationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLQuotation
        fields = [
            "partner", "product", "scheme_type",
            "quotation_date", "valid_until",
            "total_members", "total_sum_assured", "total_annual_premium",
            "experience_rating_factor", "commission_rate", "admin_loading_rate",
            "free_cover_limit", "notes",
        ]

    def create(self, validated_data):
        validated_data["quotation_number"] = GLNumberingService.generate_quotation_number()
        request = self.context.get("request")
        if request and request.user:
            validated_data["prepared_by"] = request.user
        # Snapshot FCL from product if not explicitly set
        if not validated_data.get("free_cover_limit"):
            validated_data["free_cover_limit"] = validated_data["product"].free_cover_limit
        return super().create(validated_data)


# =============================================================================
# LAYER 4 — SCHEME & MEMBER SERIALIZERS
# =============================================================================


class GLSchemeCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = GLSchemeCategory
        fields = [
            "id", "scheme", "category_name", "description",
            "salary_multiple", "flat_sum_assured",
            "premium_rate_per_mille",
            "min_entry_age", "max_entry_age", "max_cover_age",
            "sort_order", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLSchemeRiderSerializer(serializers.ModelSerializer):
    rider_name = serializers.ReadOnlyField(source="rider.name")
    rider_type = serializers.ReadOnlyField(source="rider.rider_type")

    class Meta:
        model = GLSchemeRider
        fields = [
            "id", "scheme", "rider", "rider_name", "rider_type",
            "rate_per_mille", "flat_amount", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLSchemeListSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()
    product_name = serializers.ReadOnlyField(source="product.name")
    scheme_type_name = serializers.ReadOnlyField(source="scheme_type.name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)

    class Meta:
        model = GLScheme
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


class GLSchemeDetailSerializer(serializers.ModelSerializer):
    partner_name = serializers.SerializerMethodField()
    product_name = serializers.ReadOnlyField(source="product.name")
    product_code = serializers.ReadOnlyField(source="product.code")
    scheme_type_name = serializers.ReadOnlyField(source="scheme_type.name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    categories = GLSchemeCategorySerializer(many=True, read_only=True)
    riders = GLSchemeRiderSerializer(many=True, read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    days_until_expiry = serializers.IntegerField(read_only=True)
    converted_from_quotation_number = serializers.ReadOnlyField(
        source="converted_from_quotation.quotation_number"
    )

    class Meta:
        model = GLScheme
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


class GLSchemeCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLScheme
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
        validated_data["scheme_number"] = GLNumberingService.generate_scheme_number()
        request = self.context.get("request")
        if request and request.user:
            validated_data["created_by"] = request.user
        return super().create(validated_data)


class GLSchemeMemberDependentSerializer(serializers.ModelSerializer):
    relationship_display = serializers.CharField(source="get_relationship_display", read_only=True)

    class Meta:
        model = GLSchemeMemberDependent
        fields = [
            "id", "member", "relationship", "relationship_display",
            "first_name", "surname", "gender", "date_of_birth",
            "sum_assured", "premium_amount",
            "cover_start_date", "cover_end_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLSchemeMemberListSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    category_name = serializers.ReadOnlyField(source="category.category_name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    uw_status_display = serializers.CharField(source="get_uw_status_display", read_only=True)

    class Meta:
        model = GLSchemeMember
        fields = [
            "id", "member_number", "scheme", "scheme_number",
            "category", "category_name",
            "status", "status_name", "status_code",
            "first_name", "surname", "full_name", "gender",
            "date_of_birth", "age",
            "employee_number", "job_title", "annual_salary",
            "sum_assured", "premium_amount",
            "cover_start_date", "cover_end_date",
            "requires_medical_uw", "uw_status", "uw_status_display",
            "created_at",
        ]


class GLSchemeMemberDetailSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    category_name = serializers.ReadOnlyField(source="category.category_name")
    status_name = serializers.ReadOnlyField(source="status.name")
    status_code = serializers.ReadOnlyField(source="status.code")
    full_name = serializers.CharField(read_only=True)
    age = serializers.IntegerField(read_only=True)
    uw_status_display = serializers.CharField(source="get_uw_status_display", read_only=True)
    dependents = GLSchemeMemberDependentSerializer(many=True, read_only=True)

    class Meta:
        model = GLSchemeMember
        fields = [
            "id", "member_number",
            "scheme", "scheme_number",
            "category", "category_name",
            "status", "status_name", "status_code",
            "first_name", "surname", "other_name", "full_name",
            "gender", "date_of_birth", "age",
            "identification_type", "identification_number", "nationality",
            "employee_number", "job_title", "date_of_employment", "annual_salary",
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


class GLSchemeMemberCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLSchemeMember
        fields = [
            "scheme", "category", "status",
            "first_name", "surname", "other_name",
            "gender", "date_of_birth",
            "identification_type", "identification_number", "nationality",
            "employee_number", "job_title", "date_of_employment", "annual_salary",
            "sum_assured", "premium_amount",
            "cover_start_date", "cover_end_date",
            "email", "mobile_number", "physical_address",
            "beneficiary_details",
        ]

    def create(self, validated_data):
        validated_data["member_number"] = GLNumberingService.generate_member_number()

        # Auto-flag FCL
        scheme = validated_data.get("scheme")
        sum_assured = validated_data.get("sum_assured", 0)
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


class GLMedicalCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLMedicalCode
        fields = [
            "id", "code", "name", "description", "icd10_code",
            "category", "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLMedicalLimitSerializer(serializers.ModelSerializer):
    product_name = serializers.ReadOnlyField(source="product.name")

    class Meta:
        model = GLMedicalLimit
        fields = [
            "id", "product", "product_name",
            "age_from", "age_to",
            "sum_assured_from", "sum_assured_to",
            "required_tests", "description", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLUnderwritingDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLUnderwritingDecision
        fields = [
            "id", "code", "name", "description", "sort_order",
            "is_active", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLPersonalHabitSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    risk_level_display = serializers.CharField(source="get_risk_level_display", read_only=True)

    class Meta:
        model = GLPersonalHabit
        fields = [
            "id", "code", "name", "category", "category_display",
            "risk_level", "risk_level_display", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLMedicalHistorySerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)
    risk_impact_display = serializers.CharField(source="get_risk_impact_display", read_only=True)

    class Meta:
        model = GLMedicalHistory
        fields = [
            "id", "code", "name", "category", "category_display",
            "risk_impact", "risk_impact_display", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLMedicalFacilitySerializer(serializers.ModelSerializer):
    facility_type_display = serializers.CharField(source="get_facility_type_display", read_only=True)

    class Meta:
        model = GLMedicalFacility
        fields = [
            "id", "code", "name", "facility_type", "facility_type_display",
            "address", "city", "region", "phone", "email", "contact_person",
            "is_approved", "approved_date", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLMedicalPractitionerSerializer(serializers.ModelSerializer):
    facility_name = serializers.ReadOnlyField(source="facility.name")

    class Meta:
        model = GLMedicalPractitioner
        fields = [
            "id", "code", "name", "specialization", "license_number",
            "facility", "facility_name", "phone", "email",
            "is_approved", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLMedicalCaseListSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source="member.full_name")
    member_number = serializers.ReadOnlyField(source="member.member_number")
    facility_name = serializers.ReadOnlyField(source="facility.name")
    decision_name = serializers.ReadOnlyField(source="decision.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = GLMedicalCase
        fields = [
            "id", "case_number", "member", "member_name", "member_number",
            "facility", "facility_name",
            "status", "status_display",
            "decision", "decision_name",
            "examination_date", "premium_loading_percent",
            "created_at",
        ]


class GLMedicalCaseDetailSerializer(serializers.ModelSerializer):
    member_name = serializers.ReadOnlyField(source="member.full_name")
    member_number = serializers.ReadOnlyField(source="member.member_number")
    facility_name = serializers.ReadOnlyField(source="facility.name")
    practitioner_name = serializers.ReadOnlyField(source="practitioner.name")
    decision_name = serializers.ReadOnlyField(source="decision.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    diagnosis_codes = GLMedicalCodeSerializer(many=True, read_only=True)
    personal_habits = GLPersonalHabitSerializer(many=True, read_only=True)
    medical_history = GLMedicalHistorySerializer(many=True, read_only=True)
    questionnaire_name = serializers.ReadOnlyField(source="questionnaire.name")
    decided_by_name = serializers.SerializerMethodField()

    class Meta:
        model = GLMedicalCase
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


class GLMedicalCaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLMedicalCase
        fields = [
            "member", "facility", "practitioner",
            "examination_date", "questionnaire",
        ]

    def create(self, validated_data):
        validated_data["case_number"] = GLNumberingService.generate_medical_case_number()
        return super().create(validated_data)


# =============================================================================
# LAYER 6 — CLAIMS SERIALIZERS
# =============================================================================


class GLClaimTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLClaimType
        fields = [
            "id", "code", "name", "description",
            "requires_medical_report", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLClaimReasonSerializer(serializers.ModelSerializer):
    claim_type_name = serializers.ReadOnlyField(source="claim_type.name")

    class Meta:
        model = GLClaimReason
        fields = [
            "id", "code", "name", "claim_type", "claim_type_name",
            "description", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLClaimStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLClaimStatus
        fields = [
            "id", "code", "name", "description",
            "sort_order", "is_terminal", "is_active",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLDischargeTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLDischargeType
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLCorrespondentTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLCorrespondentType
        fields = ["id", "code", "name", "description", "is_active", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLClaimInstallmentSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = GLClaimInstallment
        fields = [
            "id", "claim", "installment_number",
            "due_date", "amount", "paid_amount",
            "status", "status_display",
            "payment_reference", "payment_date", "notes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class GLClaimListSerializer(serializers.ModelSerializer):
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
        model = GLClaim
        fields = [
            "id", "claim_number",
            "scheme", "scheme_number",
            "member", "member_name", "member_number",
            "claim_type", "claim_type_name",
            "status", "status_name", "status_code",
            "incident_date", "notification_date",
            "claim_amount", "approved_amount", "paid_amount", "outstanding_amount",
            "currency", "reinsurance_notified",
            "created_at",
        ]


class GLClaimDetailSerializer(serializers.ModelSerializer):
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
    installments = GLClaimInstallmentSerializer(many=True, read_only=True)

    class Meta:
        model = GLClaim
        fields = [
            "id", "claim_number",
            "scheme", "scheme_number",
            "member", "member_name", "member_number",
            "claim_type", "claim_type_name",
            "claim_reason", "claim_reason_name",
            "status", "status_name", "status_code",
            "incident_date", "notification_date", "registration_date",
            "sum_assured_at_claim", "claim_amount", "approved_amount",
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


class GLClaimCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLClaim
        fields = [
            "scheme", "member", "claim_type", "claim_reason", "status",
            "incident_date", "notification_date",
            "sum_assured_at_claim", "claim_amount",
            "claimant_name", "claimant_relationship", "claimant_id_number",
            "claimant_phone", "claimant_email",
            "claimant_bank_name", "claimant_bank_account",
        ]

    def create(self, validated_data):
        validated_data["claim_number"] = GLNumberingService.generate_claim_number()
        request = self.context.get("request")
        if request and request.user:
            validated_data["registered_by"] = request.user
        # Snapshot member's current sum assured
        member = validated_data.get("member")
        if member and not validated_data.get("sum_assured_at_claim"):
            validated_data["sum_assured_at_claim"] = member.sum_assured
        return super().create(validated_data)


class GLMedicalInvoiceSerializer(serializers.ModelSerializer):
    facility_name = serializers.ReadOnlyField(source="facility.name")
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = GLMedicalInvoice
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


class GLSchemeRenewalListSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    renewal_status_name = serializers.ReadOnlyField(source="renewal_status.name")
    renewal_status_code = serializers.ReadOnlyField(source="renewal_status.code")

    class Meta:
        model = GLSchemeRenewal
        fields = [
            "id", "renewal_number", "scheme", "scheme_number",
            "renewal_status", "renewal_status_name", "renewal_status_code",
            "current_expiry_date", "proposed_renewal_date",
            "previous_premium", "proposed_premium",
            "claims_experience_ratio",
            "created_at",
        ]


class GLSchemeRenewalDetailSerializer(serializers.ModelSerializer):
    scheme_number = serializers.ReadOnlyField(source="scheme.scheme_number")
    renewal_status_name = serializers.ReadOnlyField(source="renewal_status.name")

    class Meta:
        model = GLSchemeRenewal
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


class GLSchemeRenewalCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = GLSchemeRenewal
        fields = [
            "scheme", "renewal_status",
            "current_expiry_date", "proposed_renewal_date",
            "previous_premium", "proposed_premium",
            "previous_experience_factor", "proposed_experience_factor",
            "claims_experience_ratio", "notes",
        ]

    def create(self, validated_data):
        validated_data["renewal_number"] = GLNumberingService.generate_renewal_number()
        request = self.context.get("request")
        if request and request.user:
            validated_data["initiated_by"] = request.user
        return super().create(validated_data)

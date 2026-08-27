from rest_framework import serializers

from .models import (
    OLClaim,
    OLClaimDocument,
    OLClaimFileNote,
    OLClaimItem,
    OLClaimRequisition,
    OLClaimant,
)


def _partner_name(partner):
    if not partner:
        return "Unassigned"
    legal_name = getattr(partner, "legal_name", "") or ""
    if legal_name:
        return legal_name
    return " ".join(
        part
        for part in (
            getattr(partner, "first_name", ""),
            getattr(partner, "other_name", ""),
            getattr(partner, "surname", ""),
        )
        if part
    ) or getattr(partner, "partner_number", "") or "Unassigned"


def _partner_display(partner):
    if not partner:
        return "Unassigned"
    number = getattr(partner, "partner_number", "") or ""
    return " — ".join(part for part in (number, _partner_name(partner)) if part)


class OLClaimantSerializer(serializers.ModelSerializer):
    claimant_type_display = serializers.CharField(source="get_claimant_type_display", read_only=True)

    class Meta:
        model = OLClaimant
        fields = (
            "id",
            "claimant_type",
            "claimant_type_display",
            "relationship",
            "name",
            "identity_number",
            "age",
            "gender",
            "is_active",
        )
        read_only_fields = fields


class OLClaimItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OLClaimItem
        fields = (
            "id",
            "benefit_type",
            "sum_assured",
            "calculated_amount",
            "approved_amount",
            "adjustment_reason",
        )
        read_only_fields = fields


class OLClaimDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_display = serializers.SerializerMethodField()

    class Meta:
        model = OLClaimDocument
        fields = (
            "id",
            "document_type",
            "file_reference",
            "mandatory_flag",
            "uploaded_by_display",
            "upload_date",
        )
        read_only_fields = fields

    def get_uploaded_by_display(self, obj):
        user = obj.uploaded_by
        return user.get_full_name() or user.email if user else "System"


class OLClaimFileNoteSerializer(serializers.ModelSerializer):
    created_by_display = serializers.SerializerMethodField()

    class Meta:
        model = OLClaimFileNote
        fields = ("id", "note_text", "created_by_display", "created_at")
        read_only_fields = fields

    def get_created_by_display(self, obj):
        user = obj.created_by
        return user.get_full_name() or user.email if user else "System"


class OLClaimRequisitionSerializer(serializers.ModelSerializer):
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = OLClaimRequisition
        fields = (
            "id",
            "requisition_number",
            "amount",
            "bank_details_json",
            "status",
            "status_display",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class OLClaimListSerializer(serializers.ModelSerializer):
    policy_number = serializers.CharField(source="policy_ref.policy_number", read_only=True)
    policyholder_name = serializers.SerializerMethodField()
    policyholder_display = serializers.SerializerMethodField()
    product_display = serializers.CharField(source="policy_ref.product_plan_ref", read_only=True)
    currency = serializers.CharField(source="policy_ref.currency", read_only=True)
    amount = serializers.SerializerMethodField()
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = OLClaim
        fields = (
            "id",
            "claim_number",
            "policy_number",
            "policyholder_name",
            "policyholder_display",
            "product_display",
            "claim_type",
            "claim_date",
            "admitted_date",
            "amount",
            "currency",
            "status",
            "status_display",
            "fraud_flag",
            "allowed_actions",
        )
        read_only_fields = fields

    def get_policyholder_name(self, obj):
        return _partner_name(obj.policy_ref.partner)

    def get_policyholder_display(self, obj):
        return _partner_display(obj.policy_ref.partner)

    def get_amount(self, obj):
        return sum((item.approved_amount or item.calculated_amount for item in obj.items.all()), 0)

    def get_allowed_actions(self, obj):
        return _allowed_actions(obj.status)


class OLClaimDetailSerializer(OLClaimListSerializer):
    claimant = serializers.SerializerMethodField()
    items = OLClaimItemSerializer(many=True, read_only=True)
    documents = OLClaimDocumentSerializer(many=True, read_only=True)
    file_notes = OLClaimFileNoteSerializer(many=True, read_only=True)
    requisition = OLClaimRequisitionSerializer(read_only=True)
    registered_by_display = serializers.SerializerMethodField()
    admitted_by_display = serializers.SerializerMethodField()
    source_channel_display = serializers.CharField(source="get_source_channel_display", read_only=True)
    medical_status_display = serializers.CharField(source="get_medical_status_display", read_only=True)
    medical_reviewed_by_display = serializers.SerializerMethodField()
    policy_context = serializers.SerializerMethodField()

    class Meta(OLClaimListSerializer.Meta):
        fields = OLClaimListSerializer.Meta.fields + (
            "cause_of_claim",
            "description",
            "assessment_notes",
            "fraud_flag_reason",
            "waiver_of_premium_days",
            "waiver_of_premium_until",
            "waiver_of_premium_applied",
            "settled_date",
            "source_channel",
            "source_channel_display",
            "medical_status",
            "medical_status_display",
            "medical_result",
            "medical_reason",
            "medical_requested_at",
            "medical_reviewed_by_display",
            "medical_reviewed_at",
            "medical_loading_factor",
            "registered_by_display",
            "admitted_by_display",
            "claimant",
            "items",
            "documents",
            "file_notes",
            "requisition",
            "policy_context",
            "created_at",
            "updated_at",
        )

    def get_claimant(self, obj):
        claimant = obj.claimant_ref or obj.claimants.filter(is_active=True).first()
        return OLClaimantSerializer(claimant).data if claimant else None

    def get_registered_by_display(self, obj):
        user = obj.registered_by
        return user.get_full_name() or user.email if user else "System"

    def get_admitted_by_display(self, obj):
        user = obj.admitted_by
        return user.get_full_name() or user.email if user else "System"

    def get_medical_reviewed_by_display(self, obj):
        user = obj.medical_reviewed_by
        return user.get_full_name() or user.email if user else "System"

    def get_policy_context(self, obj):
        policy = obj.policy_ref
        return {
            "policy_number": policy.policy_number,
            "policyholder_display": _partner_display(policy.partner),
            "product_display": policy.product_plan_ref,
            "currency": policy.currency,
            "policy_status": policy.status,
            "risk_commencement_date": policy.risk_commencement_date,
            "maturity_date": policy.maturity_date,
        }


def _allowed_actions(status):
    return {
        "REGISTERED": ["view", "assess", "cancel", "print"],
        "PENDING_MEDICAL": ["view", "cancel", "print"],
        "ASSESSMENT": ["view", "assess", "cancel", "print"],
        "ASSESSED": ["view", "requisition", "cancel", "print"],
        "REQUISITION": ["view", "requisition", "print"],
        "REQUISITIONED": ["view", "print"],
        "APPROVED": ["view", "settle", "print"],
        "SETTLED": ["view", "print"],
        "REJECTED": ["view", "print"],
        "CANCELLED": ["view", "print"],
    }.get((status or "").upper(), ["view"])

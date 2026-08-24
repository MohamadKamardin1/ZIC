from rest_framework import serializers

from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptDocument,
    ReceiptReversal,
    ReceiptStatusHistory,
)
from apps.front_office.receipts.services.parameter_resolver import payment_mode_label

_ALLOWED_BY_STATUS = {
    "DRAFT": ["update", "post", "cancel"],
    "POSTED": ["allocate"],
    "PARTIALLY_ALLOCATED": ["allocate"],
    "FULLY_ALLOCATED": ["reverse"],
    "REVERSED": [],
    "CANCELLED": [],
}


def allowed_actions(receipt):
    return list(_ALLOWED_BY_STATUS.get(receipt.status, []))


def _actor_name(actor):
    if actor is None:
        return None
    if hasattr(actor, "get_full_name"):
        full = actor.get_full_name() or ""
        if full:
            return full
    return getattr(actor, "username", None) or str(actor)


class ReceiptAllocationSerializer(serializers.ModelSerializer):
    allocated_by = serializers.SerializerMethodField()
    allocated_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptAllocation
        fields = (
            "id",
            "target_type",
            "target_id",
            "target_display",
            "amount",
            "currency",
            "exchange_rate",
            "allocation_status",
            "reversal_of",
            "narration",
            "allocated_at",
            "allocated_by",
            "allocated_by_name",
            "source_channel",
        )

    def get_allocated_by(self, obj):
        return getattr(obj, "allocated_by_id", None)

    def get_allocated_by_name(self, obj):
        return _actor_name(obj.allocated_by)


class ReceiptReversalSerializer(serializers.ModelSerializer):
    reversed_by = serializers.SerializerMethodField()
    reversed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptReversal
        fields = (
            "id",
            "reversal_number",
            "reason",
            "reversed_allocations",
            "reversed_at",
            "reversed_by",
            "reversed_by_name",
        )

    def get_reversed_by(self, obj):
        return getattr(obj, "reversed_by_id", None)

    def get_reversed_by_name(self, obj):
        return _actor_name(obj.reversed_by)


class ReceiptDocumentSerializer(serializers.ModelSerializer):
    uploaded_by = serializers.SerializerMethodField()
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptDocument
        fields = (
            "id",
            "document_type",
            "document_number",
            "file_reference",
            "filename",
            "mime_type",
            "status",
            "uploaded_at",
            "uploaded_by",
            "uploaded_by_name",
        )

    def get_uploaded_by(self, obj):
        return getattr(obj, "uploaded_by_id", None)

    def get_uploaded_by_name(self, obj):
        return _actor_name(obj.uploaded_by)


class ReceiptStatusHistorySerializer(serializers.ModelSerializer):
    changed_by = serializers.SerializerMethodField()
    changed_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptStatusHistory
        fields = ("id", "from_status", "to_status", "reason", "changed_at", "changed_by", "changed_by_name", "source_channel")

    def get_changed_by(self, obj):
        return getattr(obj, "changed_by_id", None)

    def get_changed_by_name(self, obj):
        return _actor_name(obj.changed_by)


class ReceiptBaseSerializer(serializers.ModelSerializer):
    branch = serializers.UUIDField(source="branch_id", allow_null=True, required=False)
    branch_name = serializers.SerializerMethodField()
    partner = serializers.UUIDField(source="partner_id", allow_null=True, required=False)
    partner_name = serializers.SerializerMethodField()
    payer_name = serializers.SerializerMethodField()
    bank_account = serializers.UUIDField(source="bank_account_id", allow_null=True, required=False)
    bank_account_name = serializers.SerializerMethodField()
    payment_mode_label = serializers.SerializerMethodField()
    posted_by = serializers.SerializerMethodField()
    posted_by_name = serializers.SerializerMethodField()
    reversed_by = serializers.SerializerMethodField()
    reversed_by_name = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = (
            "id",
            "receipt_number",
            "receipt_date",
            "branch",
            "branch_name",
            "partner",
            "partner_name",
            "payer_name",
            "payer_identity",
            "source_module",
            "source_reference_type",
            "source_reference_id",
            "currency",
            "exchange_rate",
            "receipt_amount",
            "allocated_amount",
            "unallocated_amount",
            "payment_mode",
            "payment_mode_label",
            "payment_reference",
            "bank_account",
            "bank_account_name",
            "narration",
            "status",
            "posted_at",
            "posted_by",
            "posted_by_name",
            "reversed_at",
            "reversed_by",
            "reversed_by_name",
            "cancellation_reason",
            "source_channel",
            "allowed_actions",
            "created_at",
            "updated_at",
        )

    def get_branch_name(self, obj):
        return obj.branch_name_snapshot or (str(obj.branch) if obj.branch_id else None)

    def get_partner_name(self, obj):
        return obj.partner_name_snapshot or (str(obj.partner) if obj.partner_id else None)

    def get_payer_name(self, obj):
        return obj.payer_name

    def get_bank_account_name(self, obj):
        return obj.bank_account_snapshot or (str(obj.bank_account) if obj.bank_account_id else None)

    def get_payment_mode_label(self, obj):
        return payment_mode_label(obj.payment_mode)

    def get_posted_by(self, obj):
        return getattr(obj, "posted_by_id", None)

    def get_posted_by_name(self, obj):
        return _actor_name(obj.posted_by)

    def get_reversed_by(self, obj):
        return getattr(obj, "reversed_by_id", None)

    def get_reversed_by_name(self, obj):
        return _actor_name(obj.reversed_by)

    def get_allowed_actions(self, obj):
        return allowed_actions(obj)


class ReceiptDetailSerializer(ReceiptBaseSerializer):
    allocations = ReceiptAllocationSerializer(many=True, read_only=True)
    reversals = ReceiptReversalSerializer(many=True, read_only=True)
    documents = ReceiptDocumentSerializer(many=True, read_only=True)
    status_history = ReceiptStatusHistorySerializer(many=True, read_only=True)

    class Meta(ReceiptBaseSerializer.Meta):
        fields = ReceiptBaseSerializer.Meta.fields + (
            "allocations",
            "reversals",
            "documents",
            "status_history",
        )


class ReceiptDraftSerializer(serializers.ModelSerializer):
    branch = serializers.UUIDField(required=False, allow_null=True)
    partner = serializers.UUIDField(required=False, allow_null=True)
    bank_account = serializers.UUIDField(required=False, allow_null=True)

    class Meta:
        model = Receipt
        fields = (
            "receipt_number",
            "idempotency_key",
            "receipt_date",
            "branch",
            "partner",
            "payer_name",
            "payer_identity",
            "source_module",
            "source_reference_type",
            "source_reference_id",
            "currency",
            "exchange_rate",
            "receipt_amount",
            "payment_mode",
            "payment_reference",
            "bank_account",
            "narration",
        )
        extra_kwargs = {
            "receipt_number": {"required": False, "allow_blank": True},
            "receipt_date": {"required": False},
            "payer_name": {"required": False, "allow_blank": True},
            "currency": {"required": False},
            "exchange_rate": {"required": False},
            "source_module": {"required": False},
        }

    def to_internal_value(self, data):
        internal = super().to_internal_value(data)
        for key in ("branch", "partner", "bank_account"):
            if key in internal:
                internal[f"{key}_id"] = internal.pop(key)
        return internal

    def create(self, validated_data):
        from apps.front_office.receipts.services.receipt_service import create_draft

        actor = self.context.get("request").user if self.context.get("request") else None
        source_channel = self.context.get("source_channel") or "API"
        receipt, _created = create_draft(actor=actor, source_channel=source_channel, **validated_data)
        return receipt

    def update(self, instance, validated_data):
        from apps.front_office.receipts.services.receipt_service import update_draft

        actor = self.context.get("request").user if self.context.get("request") else None
        return update_draft(instance, actor=actor, **validated_data)

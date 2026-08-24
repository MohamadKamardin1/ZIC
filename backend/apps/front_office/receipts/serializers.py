from decimal import Decimal

from rest_framework import serializers

from apps.front_office.receipts.models import (
    Receipt,
    ReceiptAllocation,
    ReceiptAllocationTargetType,
    ReceiptDocument,
    ReceiptReversal,
    ReceiptStatusHistory,
)
from apps.front_office.receipts.services.parameter_resolver import payment_mode_label

_ALLOWED_BY_STATUS = {
    "DRAFT": ["update", "post", "cancel"],
    "POSTED": ["allocate", "reverse"],
    "PARTIALLY_ALLOCATED": ["allocate", "reverse"],
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
    commitment = serializers.UUIDField(source="commitment_id", allow_null=True, required=False)
    commitment_number = serializers.SerializerMethodField()
    ol_commitment_allocation = serializers.UUIDField(
        source="ol_commitment_allocation_id", allow_null=True, required=False
    )
    allocation_amount_in_receipt_currency = serializers.SerializerMethodField()
    allocation_amount_in_target_currency = serializers.SerializerMethodField()

    class Meta:
        model = ReceiptAllocation
        fields = (
            "id",
            "target_type",
            "target_id",
            "target_display",
            "commitment",
            "commitment_number",
            "ol_commitment_allocation",
            "amount",
            "allocation_amount_in_receipt_currency",
            "allocation_amount_in_target_currency",
            "currency",
            "exchange_rate",
            "exchange_rate_used",
            "exchange_rate_source",
            "converted_amount",
            "converted_currency",
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

    def get_commitment_number(self, obj):
        if obj.commitment_id:
            return obj.commitment.commitment_number
        return obj.target_display or obj.target_id or None

    def get_allocation_amount_in_receipt_currency(self, obj):
        return str(obj.amount)

    def get_allocation_amount_in_target_currency(self, obj):
        return str(obj.converted_amount)


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
    branch_display = serializers.SerializerMethodField()
    partner_display = serializers.SerializerMethodField()
    currency_display = serializers.SerializerMethodField()
    payment_mode_display = serializers.SerializerMethodField()
    bank_account_display = serializers.SerializerMethodField()
    created_by_display = serializers.SerializerMethodField()
    posted_by_display = serializers.SerializerMethodField()

    class Meta:
        model = Receipt
        fields = (
            "id",
            "receipt_number",
            "receipt_date",
            "branch",
            "branch_name",
            "branch_display",
            "partner",
            "partner_name",
            "partner_display",
            "payer_name",
            "payer_identity",
            "source_module",
            "source_reference_type",
            "source_reference_id",
            "currency",
            "currency_display",
            "exchange_rate",
            "receipt_amount",
            "allocated_amount",
            "unallocated_amount",
            "payment_mode",
            "payment_mode_label",
            "payment_mode_display",
            "payment_reference",
            "bank_account",
            "bank_account_name",
            "bank_account_display",
            "narration",
            "status",
            "posted_at",
            "posted_by",
            "posted_by_name",
            "posted_by_display",
            "reversed_at",
            "reversed_by",
            "reversed_by_name",
            "cancellation_reason",
            "source_channel",
            "allowed_actions",
            "created_by_display",
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

    def get_branch_display(self, obj):
        return obj.branch_name_snapshot or (str(obj.branch) if obj.branch_id else None)

    def get_partner_display(self, obj):
        return obj.partner_name_snapshot or (str(obj.partner) if obj.partner_id else None)

    def get_currency_display(self, obj):
        return obj.currency

    def get_payment_mode_display(self, obj):
        return payment_mode_label(obj.payment_mode)

    def get_bank_account_display(self, obj):
        return obj.bank_account_snapshot or (str(obj.bank_account) if obj.bank_account_id else None)

    def get_created_by_display(self, obj):
        return _actor_name(obj.created_by)

    def get_posted_by_display(self, obj):
        return _actor_name(obj.posted_by)

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
    # The idempotency key's uniqueness is enforced by create_draft (a duplicate
    # key returns the existing receipt); the model UniqueValidator would reject
    # a legitimate retry before the service's idempotency guard runs.
    idempotency_key = serializers.CharField(
        required=False, allow_blank=True, allow_null=True, max_length=64, validators=[]
    )

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
        receipt, created = create_draft(actor=actor, source_channel=source_channel, **validated_data)
        self._created = created
        return receipt

    def update(self, instance, validated_data):
        from apps.front_office.receipts.services.receipt_service import update_draft

        actor = self.context.get("request").user if self.context.get("request") else None
        return update_draft(instance, actor=actor, **validated_data)


class ReceiptReasonSerializer(serializers.Serializer):
    """Mandatory reason for reversal, allocation reversal, and cancellation."""

    reason = serializers.CharField(
        required=True,
        allow_blank=False,
        max_length=2000,
        error_messages={
            "required": "A reason is required for this action.",
            "blank": "A reason is required for this action.",
        },
    )


class ReceiptAllocationRequestSerializer(serializers.Serializer):
    """Manual allocation payload: OL_COMMITMENT target, amount, optional rate.

    Cross-currency allocations require a positive ``exchange_rate`` (from the
    receipt currency to the target commitment currency) unless an active rate is
    on file for the pair; ``exchange_rate_source`` records provenance.
    """

    target_type = serializers.ChoiceField(
        choices=[ReceiptAllocationTargetType.OL_COMMITMENT],
        error_messages={"invalid_choice": "Only OL_COMMITMENT allocations are supported."},
    )
    target_id = serializers.CharField(max_length=120, allow_blank=False)
    amount = serializers.DecimalField(max_digits=18, decimal_places=2, min_value=Decimal("0.01"))
    exchange_rate = serializers.DecimalField(
        max_digits=18,
        decimal_places=8,
        required=False,
        allow_null=True,
        min_value=Decimal("0.00000001"),
    )
    exchange_rate_source = serializers.CharField(required=False, allow_blank=True, default="")
    narration = serializers.CharField(required=False, allow_blank=True, default="")

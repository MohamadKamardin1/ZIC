from rest_framework import serializers

from .models import OLParameterTableRegistry


class OLParameterBaseSerializer(serializers.Serializer):
    """Framework-level serializer contract for future concrete OL parameters."""

    id = serializers.UUIDField(read_only=True)
    code = serializers.CharField(max_length=100)
    name = serializers.CharField(max_length=200)
    description = serializers.CharField(required=False, allow_blank=True)
    is_active = serializers.BooleanField(required=False)
    effective_from = serializers.DateField(required=False, allow_null=True)
    effective_to = serializers.DateField(required=False, allow_null=True)
    created_by = serializers.UUIDField(read_only=True)
    updated_by = serializers.UUIDField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def validate(self, attrs):
        effective_from = attrs.get("effective_from")
        effective_to = attrs.get("effective_to")
        if effective_from and effective_to and effective_to < effective_from:
            raise serializers.ValidationError(
                {"effective_to": "Effective-to cannot be before effective-from."}
            )
        return attrs


class OLTableRegistrySerializer(serializers.ModelSerializer):
    required_permissions = serializers.SerializerMethodField()

    class Meta:
        model = OLParameterTableRegistry
        fields = [
            "id",
            "slug",
            "label",
            "description",
            "parameter_group",
            "model_label",
            "visible_columns",
            "searchable_fields",
            "filter_fields",
            "default_ordering",
            "allowed_actions",
            "export_support",
            "permission_code",
            "permission_requirements",
            "required_permissions",
            "is_active",
            "created_by",
            "updated_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by", "updated_by", "created_at", "updated_at"]

    def get_required_permissions(self, obj):
        requirements = obj.permission_requirements or {}
        if not requirements:
            return {"view": obj.permission_code}
        return requirements

    def validate_permission_code(self, value):
        normalized = (value or "").strip().lower()
        if "." not in normalized:
            raise serializers.ValidationError("Permission code must use module.action notation.")
        return normalized

    def validate(self, attrs):
        for field_name in ("visible_columns", "searchable_fields", "filter_fields", "default_ordering", "allowed_actions"):
            value = attrs.get(field_name)
            if value is not None and (not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value)):
                raise serializers.ValidationError({field_name: "Expected a list of non-empty strings."})
        if "permission_requirements" in attrs and not isinstance(attrs["permission_requirements"], dict):
            raise serializers.ValidationError({"permission_requirements": "Expected a JSON object."})
        return attrs


import json
from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError as DjangoValidationError

from .models import (
    OLCommissionRateType,
    OLComputationApproach,
    OLDefaultParameterValueType,
    OLDefaultSystemParameter,
    OLMaturityClaimSetup,
    OLOverrideCommissionSetup,
)


_AUDIT_READ_ONLY = ["id", "created_by", "updated_by", "created_at", "updated_at"]


class OLDefaultSystemParameterSerializer(serializers.ModelSerializer):
    typed_value = serializers.JSONField(required=False, allow_null=True, write_only=True)
    value = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = OLDefaultSystemParameter
        fields = [
            "id", "code", "parameter_key", "name", "parameter_category", "description",
            "value_type", "typed_value", "value", "string_value", "integer_value",
            "decimal_value", "boolean_value", "date_value", "json_value", "is_active",
            "effective_from", "effective_to", "created_by", "updated_by", "created_at", "updated_at",
        ]
        read_only_fields = _AUDIT_READ_ONLY + [
            "value", "string_value", "integer_value", "decimal_value", "boolean_value", "date_value", "json_value",
        ]
        extra_kwargs = {
            "code": {"required": False, "allow_blank": True},
            "parameter_key": {"required": False, "allow_blank": True},
        }

    def get_value(self, obj):
        value = obj.value
        if isinstance(value, Decimal):
            return str(value)
        return value

    def validate(self, attrs):
        parameter_key = (attrs.get("parameter_key") or attrs.get("code") or getattr(self.instance, "parameter_key", "")).strip().upper()
        code = (attrs.get("code") or parameter_key).strip().upper()
        if not parameter_key:
            raise serializers.ValidationError({"parameter_key": "Parameter key is required."})
        if code != parameter_key:
            raise serializers.ValidationError({"code": "Code and parameter key must match."})
        attrs["parameter_key"] = parameter_key
        attrs["code"] = code
        value_type = (attrs.get("value_type") or getattr(self.instance, "value_type", "STRING")).upper()
        if value_type not in dict(OLDefaultParameterValueType.choices):
            raise serializers.ValidationError({"value_type": "Unsupported OL default parameter value type."})
        attrs["value_type"] = value_type
        has_typed_value = "typed_value" in attrs
        if self.instance is None and not has_typed_value:
            raise serializers.ValidationError({"typed_value": "A typed value is required when creating a parameter."})
        if self.instance is not None and "value_type" in attrs and value_type != self.instance.value_type and not has_typed_value:
            raise serializers.ValidationError({"typed_value": "A typed value is required when changing value type."})
        if has_typed_value:
            raw_value = attrs.pop("typed_value")
            if raw_value is None:
                raise serializers.ValidationError({"typed_value": "A typed value cannot be null."})
            try:
                if value_type in {OLDefaultParameterValueType.STRING, OLDefaultParameterValueType.TEXT}:
                    typed_value = str(raw_value)
                    attrs["string_value"] = typed_value
                elif value_type == OLDefaultParameterValueType.INTEGER:
                    if isinstance(raw_value, bool) or (isinstance(raw_value, float) and not raw_value.is_integer()):
                        raise ValueError
                    typed_value = int(raw_value)
                    attrs["integer_value"] = typed_value
                elif value_type == OLDefaultParameterValueType.DECIMAL:
                    typed_value = Decimal(str(raw_value))
                    attrs["decimal_value"] = typed_value
                elif value_type == OLDefaultParameterValueType.BOOLEAN:
                    if isinstance(raw_value, str):
                        normalized = raw_value.strip().lower()
                        if normalized not in {"true", "false", "1", "0", "yes", "no", "on", "off"}:
                            raise ValueError
                        typed_value = normalized in {"true", "1", "yes", "on"}
                    elif isinstance(raw_value, bool):
                        typed_value = raw_value
                    else:
                        raise ValueError
                    attrs["boolean_value"] = typed_value
                elif value_type == OLDefaultParameterValueType.DATE:
                    typed_value = raw_value if isinstance(raw_value, date) else date.fromisoformat(str(raw_value))
                    attrs["date_value"] = typed_value
                else:
                    json.dumps(raw_value)
                    typed_value = raw_value
                    attrs["json_value"] = typed_value
            except (TypeError, ValueError, InvalidOperation) as exc:
                raise serializers.ValidationError({"typed_value": f"Value is not valid for type {value_type}."}) from exc
            active_field = {
                "STRING": "string_value", "TEXT": "string_value", "INTEGER": "integer_value",
                "DECIMAL": "decimal_value", "BOOLEAN": "boolean_value", "DATE": "date_value", "JSON": "json_value",
            }[value_type]
            for field_name in ("string_value", "integer_value", "decimal_value", "boolean_value", "date_value", "json_value"):
                if field_name != active_field:
                    attrs[field_name] = None
        return attrs


class _ValidatedDefaultSetupModelSerializer(serializers.ModelSerializer):
    class Meta:
        fields = "__all__"
        read_only_fields = _AUDIT_READ_ONLY

    def validate(self, attrs):
        candidate = self.instance or self.Meta.model()
        for field_name, value in attrs.items():
            setattr(candidate, field_name, value)
        try:
            candidate.full_clean(validate_unique=False)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.message_dict) from exc
        return attrs


class OLOverrideCommissionSetupSerializer(_ValidatedDefaultSetupModelSerializer):
    class Meta(_ValidatedDefaultSetupModelSerializer.Meta):
        model = OLOverrideCommissionSetup
        fields = "__all__"
        read_only_fields = _AUDIT_READ_ONLY


class OLComputationApproachSerializer(_ValidatedDefaultSetupModelSerializer):
    class Meta(_ValidatedDefaultSetupModelSerializer.Meta):
        model = OLComputationApproach
        fields = "__all__"
        read_only_fields = _AUDIT_READ_ONLY


class OLMaturityClaimSetupSerializer(_ValidatedDefaultSetupModelSerializer):
    class Meta(_ValidatedDefaultSetupModelSerializer.Meta):
        model = OLMaturityClaimSetup
        fields = "__all__"
        read_only_fields = _AUDIT_READ_ONLY

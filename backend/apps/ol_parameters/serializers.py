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

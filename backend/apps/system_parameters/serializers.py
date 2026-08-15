from rest_framework import serializers

from .models import ParameterGroup, SystemParameter, ChoiceList, ChoiceOption


class ChoiceOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChoiceOption
        fields = [
            "id", "choice_list", "code", "label", "is_default",
            "is_active", "sort_order", "metadata", "created_at", "updated_at",
        ]


class ChoiceListSerializer(serializers.ModelSerializer):
    options = ChoiceOptionSerializer(many=True, read_only=True)

    class Meta:
        model = ChoiceList
        fields = [
            "id", "group", "code", "name", "description",
            "is_active", "options", "created_at", "updated_at",
        ]


class SystemParameterSerializer(serializers.ModelSerializer):
    value = serializers.ReadOnlyField()
    group_name = serializers.ReadOnlyField(source="group.name")

    class Meta:
        model = SystemParameter
        fields = [
            "id", "group", "group_name", "name", "code", "description",
            "value_type", "value",
            "string_value", "integer_value", "float_value",
            "boolean_value", "json_value", "file_value",
            "is_active", "is_encrypted", "sort_order",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


class SystemParameterWriteSerializer(serializers.ModelSerializer):
    # A typed write surface used by the organized Settings workspace. The
    # legacy storage columns remain available for backwards compatibility.
    value = serializers.JSONField(required=False, write_only=True)

    class Meta:
        model = SystemParameter
        fields = [
            "id", "group", "name", "code", "description",
            "value_type", "value",
            "string_value", "integer_value", "float_value",
            "boolean_value", "json_value",
            "is_active", "is_encrypted", "sort_order",
        ]
        read_only_fields = ["id"]

    def validate(self, attrs):
        value_type = attrs.get("value_type")
        if value_type is None and self.instance is not None:
            value_type = self.instance.value_type
        if value_type not in dict(SystemParameter.VALUE_TYPE_CHOICES):
            raise serializers.ValidationError({"value_type": "Unsupported parameter value type."})

        if "value" in attrs:
            typed_value = attrs.pop("value")
            if value_type in {"STRING", "TEXT"}:
                attrs["string_value"] = None if typed_value is None else str(typed_value)
            elif value_type == "INTEGER":
                try:
                    attrs["integer_value"] = None if typed_value is None else int(typed_value)
                except (TypeError, ValueError) as exc:
                    raise serializers.ValidationError({"value": "Value must be an integer."}) from exc
            elif value_type == "FLOAT":
                try:
                    attrs["float_value"] = None if typed_value is None else float(typed_value)
                except (TypeError, ValueError) as exc:
                    raise serializers.ValidationError({"value": "Value must be numeric."}) from exc
            elif value_type == "BOOLEAN":
                if isinstance(typed_value, str):
                    typed_value = typed_value.strip().lower() in {"true", "1", "yes", "on"}
                attrs["boolean_value"] = None if typed_value is None else bool(typed_value)
            elif value_type == "JSON":
                attrs["json_value"] = typed_value
            elif value_type == "FILE":
                raise serializers.ValidationError({"value": "File parameters must be uploaded through the file field."})

        # Clear stale values whenever the type changes, including partial
        # updates where the caller only submits a new typed value.
        value_fields = {
            "string_value", "integer_value", "float_value", "boolean_value", "json_value"
        }
        active_field = {
            "STRING": "string_value",
            "TEXT": "string_value",
            "INTEGER": "integer_value",
            "FLOAT": "float_value",
            "BOOLEAN": "boolean_value",
            "JSON": "json_value",
        }.get(value_type)
        for field in value_fields - ({active_field} if active_field else set()):
            attrs[field] = None
        return attrs


class ParameterGroupSerializer(serializers.ModelSerializer):
    children = serializers.SerializerMethodField()
    parameter_count = serializers.SerializerMethodField()

    class Meta:
        model = ParameterGroup
        fields = [
            "id", "parent", "name", "code", "description",
            "sort_order", "is_active", "children",
            "parameter_count", "created_at", "updated_at",
        ]

    def get_children(self, obj):
        qs = obj.children.filter(is_active=True)
        return ParameterGroupSerializer(qs, many=True).data

    def get_parameter_count(self, obj):
        return obj.parameters.filter(is_active=True).count()


class ParameterGroupFlatSerializer(serializers.ModelSerializer):
    class Meta:
        model = ParameterGroup
        fields = [
            "id", "parent", "name", "code", "description",
            "sort_order", "is_active", "created_at", "updated_at",
        ]

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
    class Meta:
        model = SystemParameter
        fields = [
            "id", "group", "name", "code", "description",
            "value_type", "string_value", "integer_value",
            "float_value", "boolean_value", "json_value",
            "is_active", "is_encrypted", "sort_order",
        ]

    def validate(self, attrs):
        value_type = attrs.get("value_type")
        if value_type == "STRING":
            attrs["integer_value"] = None
            attrs["float_value"] = None
            attrs["boolean_value"] = None
            attrs["json_value"] = None
        elif value_type == "INTEGER":
            attrs["string_value"] = None
            attrs["float_value"] = None
            attrs["boolean_value"] = None
            attrs["json_value"] = None
        elif value_type == "FLOAT":
            attrs["string_value"] = None
            attrs["integer_value"] = None
            attrs["boolean_value"] = None
            attrs["json_value"] = None
        elif value_type == "BOOLEAN":
            attrs["string_value"] = None
            attrs["integer_value"] = None
            attrs["float_value"] = None
            attrs["json_value"] = None
        elif value_type == "JSON":
            attrs["string_value"] = None
            attrs["integer_value"] = None
            attrs["float_value"] = None
            attrs["boolean_value"] = None
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

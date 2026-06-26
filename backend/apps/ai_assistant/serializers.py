from rest_framework import serializers


class AnalyzePromptSerializer(serializers.Serializer):
    prompt = serializers.CharField(trim_whitespace=False)


class ExecutePartnerDataSerializer(serializers.Serializer):
    partner_type = serializers.ChoiceField(choices=["INDIVIDUAL", "CORPORATE"])
    partner_data = serializers.DictField()


class ClarificationSerializer(serializers.Serializer):
    prompt = serializers.CharField()
    missing_fields = serializers.ListField(child=serializers.CharField(), required=False, default=list)
    partial_data = serializers.DictField(required=False, default=dict)

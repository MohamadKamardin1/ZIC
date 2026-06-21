from rest_framework import serializers


class PolicyBreakdownSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    growth = serializers.FloatField()


class PolicyDataSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    growth = serializers.FloatField()
    breakdown = serializers.DictField(child=PolicyBreakdownSerializer())


class ClaimsItemSerializer(serializers.Serializer):
    percentage = serializers.IntegerField()
    count = serializers.IntegerField()


class ClaimsDataSerializer(serializers.Serializer):
    groupCredit = ClaimsItemSerializer()
    groupLife = ClaimsItemSerializer()
    ordinaryLife = ClaimsItemSerializer()
    pension = ClaimsItemSerializer()


class PartnerBreakdownItemSerializer(serializers.Serializer):
    percentage = serializers.FloatField()
    remaining = serializers.FloatField(required=False)


class PartnerCoInsurerSerializer(serializers.Serializer):
    percentage = serializers.FloatField()


class PartnersDataSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    breakdown = serializers.DictField()


class DebitedBreakdownItemSerializer(serializers.Serializer):
    amount = serializers.CharField()
    color = serializers.CharField()


class DebitedDataSerializer(serializers.Serializer):
    total = serializers.CharField()
    breakdown = serializers.DictField(child=DebitedBreakdownItemSerializer())


class QuotationPointSerializer(serializers.Serializer):
    month = serializers.CharField()
    ol = serializers.IntegerField()
    gl = serializers.IntegerField()
    gc = serializers.IntegerField()
    pen = serializers.IntegerField()


class QuotationLegendItemSerializer(serializers.Serializer):
    percentage = serializers.IntegerField()
    color = serializers.CharField()


class QuotationsDataSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    period = serializers.ChoiceField(choices=["monthly", "yearly"])
    data = QuotationPointSerializer(many=True)
    legend = serializers.DictField(child=QuotationLegendItemSerializer())


class NotificationItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    type = serializers.CharField()
    amount = serializers.CharField(required=False, allow_null=True)
    status = serializers.ChoiceField(
        choices=["Approved", "Rejected", "Pending", "Cancelled"]
    )
    date = serializers.CharField()
    unread = serializers.BooleanField()


class NotificationsDataSerializer(serializers.Serializer):
    request = serializers.IntegerField()
    approved = serializers.IntegerField()
    rejected = serializers.IntegerField()
    cancelled = serializers.IntegerField()
    unreadCount = serializers.IntegerField()
    notifications = NotificationItemSerializer(many=True)


class TodoItemSerializer(serializers.Serializer):
    id = serializers.CharField()
    text = serializers.CharField()
    date = serializers.CharField()
    completed = serializers.BooleanField()


class LeadItemSerializer(serializers.Serializer):
    rank = serializers.IntegerField()
    name = serializers.CharField()
    amount = serializers.CharField()
    trophy = serializers.CharField()


class DateInfoSerializer(serializers.Serializer):
    day = serializers.CharField()
    weekday = serializers.CharField()
    month = serializers.CharField()


class KPIsSerializer(serializers.Serializer):
    monthlyGrowth = serializers.FloatField()
    activeUsers = serializers.IntegerField()
    revenue = serializers.CharField()


class DashboardOverviewSerializer(serializers.Serializer):
    date = DateInfoSerializer()
    kpis = KPIsSerializer()
    policies = PolicyDataSerializer()
    claims = ClaimsDataSerializer()
    partners = PartnersDataSerializer()
    debited = DebitedDataSerializer()
    quotations = QuotationsDataSerializer()
    notifications = NotificationsDataSerializer()
    todos = TodoItemSerializer(many=True)
    leads = LeadItemSerializer(many=True)

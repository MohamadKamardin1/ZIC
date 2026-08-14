from django.utils import timezone
from rest_framework import serializers

from .models import CurrencyPair, CurrencyRate, DashboardAlert, DashboardNotification, DashboardTask


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
    amount = serializers.CharField(required=False, allow_null=True)
    type = serializers.CharField()
    status = serializers.CharField()
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


class DashboardTaskSerializer(serializers.ModelSerializer):
    dueAt = serializers.DateTimeField(source="due_at", required=False, allow_null=True)
    entityType = serializers.CharField(source="entity_type", required=False, allow_blank=True)
    entityId = serializers.CharField(source="entity_id", required=False, allow_blank=True)
    completedAt = serializers.DateTimeField(source="completed_at", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = DashboardTask
        fields = ["id", "title", "description", "status", "priority", "dueAt", "route", "entityType", "entityId", "completedAt", "createdAt", "updatedAt"]
        read_only_fields = ["id", "completedAt", "createdAt", "updatedAt"]


class DashboardAlertSerializer(serializers.ModelSerializer):
    entityType = serializers.CharField(source="entity_type", required=False, allow_blank=True)
    entityId = serializers.CharField(source="entity_id", required=False, allow_blank=True)
    acknowledgedAt = serializers.DateTimeField(source="acknowledged_at", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = DashboardAlert
        fields = ["id", "title", "message", "severity", "status", "route", "entityType", "entityId", "acknowledgedAt", "createdAt", "updatedAt"]
        read_only_fields = ["id", "acknowledgedAt", "createdAt", "updatedAt"]


class DashboardNotificationSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(required=False, default="SYSTEM")
    entityType = serializers.CharField(source="entity_type", required=False, allow_blank=True)
    entityId = serializers.CharField(source="entity_id", required=False, allow_blank=True)
    isRead = serializers.BooleanField(source="is_read", read_only=True)
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)

    class Meta:
        model = DashboardNotification
        fields = ["id", "kind", "title", "message", "status", "route", "entityType", "entityId", "isRead", "createdAt"]
        read_only_fields = ["id", "isRead", "createdAt"]


class CurrencyRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CurrencyRate
        fields = ["id", "rate", "provider", "as_of", "fetched_at"]
        read_only_fields = fields


class CurrencyPairSerializer(serializers.ModelSerializer):
    baseCurrency = serializers.CharField(source="base_currency")
    quoteCurrency = serializers.CharField(source="quote_currency")
    isActive = serializers.BooleanField(source="is_active", required=False)
    targetRate = serializers.DecimalField(source="target_rate", max_digits=20, decimal_places=8, required=False, allow_null=True)
    latestRate = serializers.SerializerMethodField(method_name="get_latest_rate")
    latestAsOf = serializers.SerializerMethodField(method_name="get_latest_as_of")
    isStale = serializers.SerializerMethodField(method_name="get_is_stale")
    createdAt = serializers.DateTimeField(source="created_at", read_only=True)
    updatedAt = serializers.DateTimeField(source="updated_at", read_only=True)

    class Meta:
        model = CurrencyPair
        fields = ["id", "baseCurrency", "quoteCurrency", "isActive", "targetRate", "latestRate", "latestAsOf", "isStale", "createdAt", "updatedAt"]
        read_only_fields = ["id", "latestRate", "latestAsOf", "isStale", "createdAt", "updatedAt"]

    def _latest(self, obj):
        return obj.rates.first()

    def get_latest_rate(self, obj):
        latest = self._latest(obj)
        return str(latest.rate) if latest else None

    def get_latest_as_of(self, obj):
        latest = self._latest(obj)
        return latest.as_of.isoformat() if latest else None

    def get_is_stale(self, obj):
        latest = self._latest(obj)
        return not latest or latest.as_of < timezone.localdate()

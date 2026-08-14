from decimal import Decimal, InvalidOperation

import requests
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.group_credit.models import GCScheme
from apps.group_life.models import GLScheme
from apps.ordinary_life.models import OLPolicy
from apps.partner_onboarding.models import PartnerApplication
from apps.partners.models import Partner
from apps.users.models import User

from .models import CurrencyPair, CurrencyRate, DashboardAlert, DashboardNotification, DashboardTask
from .serializers import (
    CurrencyPairSerializer,
    DashboardAlertSerializer,
    DashboardNotificationSerializer,
    DashboardOverviewSerializer,
    DashboardTaskSerializer,
)


class DashboardOverviewView(APIView):
    """
    Aggregates data from multiple sources to build the dashboard overview.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        now = timezone.now()

        # Get date info
        date_info = {
            "day": f"{now.day}{'st' if now.day in [1, 21, 31] else 'nd' if now.day == 2 else 'rd' if now.day == 3 else 'th'}",
            "weekday": now.strftime("%A"),
            "month": now.strftime("%B")
        }

        # Get KPIs
        active_users = User.objects.filter(is_active=True).count()
        # Calculate monthly growth (mock calculation for now)
        monthly_growth = 15.7  # Mock value
        revenue = "$328.5M"  # Mock value

        kpis = {
            "monthlyGrowth": monthly_growth,
            "activeUsers": active_users,
            "revenue": revenue
        }

        # Get policies data (mock data since Policy model doesn't exist)
        policies = self._get_policies_data()

        # Get claims data (mock data since Claim model doesn't exist)
        claims = self._get_claims_data()

        # Get partners data (real data from DB)
        partners = self._get_partners_data()

        # Get debited data (mock data)
        debited = self._get_debited_data()

        # Get quotations data (mock data)
        quotations = self._get_quotations_data()

        # Get notifications data (real data from PartnerApplication)
        notifications = self._get_notifications_data(request.user)

        # Get persisted dashboard tasks
        todos = self._get_todos_data(request.user)

        # Get leads (mock data)
        leads = self._get_leads_data()

        # Build complete dashboard data
        dashboard_data = {
            "date": date_info,
            "kpis": kpis,
            "policies": policies,
            "claims": claims,
            "partners": partners,
            "debited": debited,
            "quotations": quotations,
            "notifications": notifications,
            "todos": todos,
            "leads": leads
        }

        # Validate with serializer
        serializer = DashboardOverviewSerializer(data=dashboard_data)
        if serializer.is_valid():
            return Response(serializer.data)

        # If validation fails, return raw data (for debugging)
        return Response(dashboard_data)

    def _get_policies_data(self):
        """Get policies statistics (mock data)"""
        return {
            "total": 564,
            "growth": 5.7,
            "breakdown": {
                "groupCredit": {"count": 210, "growth": 6.7},
                "groupLife": {"count": 243, "growth": 7.0},
                "ordinaryLife": {"count": 111, "growth": 0.9},
                "pension": {"count": 0, "growth": 0.0}
            }
        }

    def _get_claims_data(self):
        """Get claims statistics (mock data)"""
        return {
            "groupCredit": {"percentage": 14, "count": 72},
            "groupLife": {"percentage": 26, "count": 62},
            "ordinaryLife": {"percentage": 31, "count": 131},
            "pension": {"percentage": 0, "count": 0}
        }

    def _get_partners_data(self):
        """Get real partner data from database"""
        # Count partners by type
        partner_counts = Partner.objects.values('partner_type').annotate(
            count=Count('id')
        )

        # Build breakdown by partner type
        type_map = {
            'INDIVIDUAL': 'client',
            'CORPORATE': 'intermediary',
            'AGENT': 'serviceProvider',
            'BROKER': 'coInsurer'
        }

        breakdown = {}
        total_partners = Partner.objects.count()

        for item in partner_counts:
            partner_type = item['partner_type']
            count = item['count']
            percentage = (count / total_partners * 100) if total_partners > 0 else 0

            key = type_map.get(partner_type, partner_type.lower())
            breakdown[key] = {
                "percentage": round(percentage, 1),
                "remaining": round(100 - percentage, 1)
            }

        # Ensure all keys exist
        for key in ['client', 'intermediary', 'serviceProvider', 'coInsurer']:
            if key not in breakdown:
                breakdown[key] = {"percentage": 0.0, "remaining": 100.0}

        return {
            "total": total_partners,
            "breakdown": breakdown
        }

    def _get_debited_data(self):
        """Get debited amounts (mock data)"""
        return {
            "total": "1.2B",
            "breakdown": {
                "gc": {"amount": "896.1M", "color": "#D4AF37"},
                "gl": {"amount": "82.3M", "color": "#14B8A6"},
                "ol": {"amount": "186.6M", "color": "#F97316"},
                "pen": {"amount": "0", "color": "#94A3B8"}
            }
        }

    def _get_quotations_data(self):
        """Get quotations statistics (mock data)"""
        return {
            "total": 424,
            "period": "monthly",
            "data": [
                {"month": "Oct", "ol": 45, "gl": 8, "gc": 12, "pen": 0},
                {"month": "Nov", "ol": 52, "gl": 10, "gc": 15, "pen": 0},
                {"month": "Dec", "ol": 68, "gl": 12, "gc": 18, "pen": 0},
                {"month": "Jan", "ol": 75, "gl": 15, "gc": 20, "pen": 0},
                {"month": "Feb", "ol": 88, "gl": 18, "gc": 22, "pen": 0}
            ],
            "legend": {
                "ol": {"percentage": 88, "color": "#F97316"},
                "gl": {"percentage": 6, "color": "#D4AF37"},
                "gc": {"percentage": 7, "color": "#7C3AED"},
                "pen": {"percentage": 0, "color": "#4F46E5"}
            }
        }

    def _get_notifications_data(self, user):
        """Get persisted notifications and synchronize recent onboarding events."""
        _sync_application_notifications(user)
        persisted = DashboardNotification.objects.filter(owner=user).order_by("-created_at")[:5]
        if persisted.exists():
            return {
                "request": persisted.filter(status__in=["PENDING", "SUBMITTED"]).count(),
                "approved": persisted.filter(status="APPROVED").count(),
                "rejected": persisted.filter(status="REJECTED").count(),
                "cancelled": persisted.filter(status="CANCELLED").count(),
                "unreadCount": DashboardNotification.objects.filter(owner=user, is_read=False).count(),
                "notifications": [
                    {
                        "id": str(item.id),
                        "type": item.title,
                        "status": item.status.replace("_", " ").title() or "Information",
                        "date": item.created_at.strftime("%d %b"),
                        "unread": not item.is_read,
                    }
                    for item in persisted
                ],
            }

        """Get notifications from PartnerApplication"""
        # Count by status
        status_counts = PartnerApplication.objects.values('status').annotate(
            count=Count('id')
        )

        status_map = {}
        for item in status_counts:
            status_map[item['status']] = item['count']

        # Get recent applications as notifications
        recent_apps = PartnerApplication.objects.order_by('-created_at')[:5]
        notifications = []

        for app in recent_apps:
            status_text = app.status.replace('_', ' ').title()
            notifications.append({
                "id": str(app.id),
                "type": f"Application #{app.application_number}",
                "status": status_text,
                "date": app.created_at.strftime("%d %b"),
                "unread": app.status in ['PENDING', 'SUBMITTED']
            })

        # Count unread (PENDING and SUBMITTED applications)
        unread_count = PartnerApplication.objects.filter(
            status__in=['PENDING', 'SUBMITTED']
        ).count()

        return {
            "request": status_map.get('SUBMITTED', 0),
            "approved": status_map.get('APPROVED', 0),
            "rejected": status_map.get('REJECTED', 0),
            "cancelled": status_map.get('CANCELLED', 0),
            "unreadCount": unread_count,
            "notifications": notifications
        }

    def _get_todos_data(self, user):
        """Get user-owned tasks, with a safe first-use checklist."""
        tasks = DashboardTask.objects.filter(owner=user).order_by("status", "due_at", "-created_at")[:10]
        if tasks.exists():
            return [
                {
                    "id": str(task.id),
                    "text": task.title,
                    "date": (task.due_at or task.created_at).strftime("%d %b %Y"),
                    "completed": task.status == DashboardTask.Status.DONE,
                }
                for task in tasks
            ]
        return [
            {
                "id": "seed-review",
                "text": "Review pending applications",
                "date": timezone.now().strftime("%d %b %Y"),
                "completed": False,
            },
            {
                "id": "seed-process",
                "text": "Process approved partners",
                "date": timezone.now().strftime("%d %b %Y"),
                "completed": False,
            },
        ]

    def _get_leads_data(self):
        """Get top leads (mock data)"""
        return [
            {"rank": 1, "name": "Partner Portal", "amount": "312.2M", "trophy": "🏆"},
            {"rank": 2, "name": "Corporate Sales", "amount": "259.5M", "trophy": "🥈"},
            {"rank": 3, "name": "Agency Network", "amount": "137.1M", "trophy": "🥉"}
        ]


def workspace_payload(data, message=""):
    return {
        "success": True,
        "status_code": status.HTTP_200_OK,
        "message": message,
        "data": data,
        "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"},
    }


def error_payload(message, status_code=status.HTTP_400_BAD_REQUEST):
    return Response(
        {
            "success": False,
            "status_code": status_code,
            "message": message,
            "data": None,
            "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"},
        },
        status=status_code,
    )


class DashboardTaskListCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = DashboardTask.objects.filter(owner=request.user)
        task_status = request.query_params.get("status")
        if task_status:
            queryset = queryset.filter(status=task_status.upper())
        serializer = DashboardTaskSerializer(queryset[:100], many=True)
        return Response(workspace_payload(serializer.data))

    def post(self, request):
        serializer = DashboardTaskSerializer(data=request.data)
        if not serializer.is_valid():
            return error_payload("Invalid task data.", status.HTTP_400_BAD_REQUEST)
        task = serializer.save(owner=request.user, created_by=request.user)
        if task.status == DashboardTask.Status.DONE:
            task.mark_complete()
        return Response(workspace_payload(DashboardTaskSerializer(task).data, "Task created."), status=status.HTTP_201_CREATED)


class DashboardTaskDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get_object(self, request, pk):
        return DashboardTask.objects.filter(owner=request.user, pk=pk).first()

    def patch(self, request, pk):
        task = self.get_object(request, pk)
        if not task:
            return error_payload("Task not found.", status.HTTP_404_NOT_FOUND)
        serializer = DashboardTaskSerializer(task, data=request.data, partial=True)
        if not serializer.is_valid():
            return error_payload("Invalid task data.", status.HTTP_400_BAD_REQUEST)
        task = serializer.save()
        if task.status == DashboardTask.Status.DONE and not task.completed_at:
            task.mark_complete()
        elif task.status != DashboardTask.Status.DONE and task.completed_at:
            task.completed_at = None
            task.save(update_fields=["completed_at", "updated_at"])
        return Response(workspace_payload(DashboardTaskSerializer(task).data, "Task updated."))

    def delete(self, request, pk):
        task = self.get_object(request, pk)
        if not task:
            return error_payload("Task not found.", status.HTTP_404_NOT_FOUND)
        task.delete()
        return Response(workspace_payload(None, "Task deleted."), status=status.HTTP_204_NO_CONTENT)


class DashboardAlertListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        queryset = DashboardAlert.objects.filter(owner=request.user)
        severity = request.query_params.get("severity")
        alert_status = request.query_params.get("status")
        if severity:
            queryset = queryset.filter(severity=severity.upper())
        if alert_status:
            queryset = queryset.filter(status=alert_status.upper())
        return Response(workspace_payload(DashboardAlertSerializer(queryset[:100], many=True).data))

    def post(self, request):
        serializer = DashboardAlertSerializer(data=request.data)
        if not serializer.is_valid():
            return error_payload("Invalid alert data.")
        alert = serializer.save(owner=request.user)
        return Response(workspace_payload(DashboardAlertSerializer(alert).data, "Alert created."), status=status.HTTP_201_CREATED)


class DashboardAlertDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, action):
        alert = DashboardAlert.objects.filter(owner=request.user, pk=pk).first()
        if not alert:
            return error_payload("Alert not found.", status.HTTP_404_NOT_FOUND)
        if action == "acknowledge":
            alert.status = DashboardAlert.Status.ACKNOWLEDGED
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = request.user
        elif action == "dismiss":
            alert.status = DashboardAlert.Status.DISMISSED
            alert.acknowledged_at = timezone.now()
            alert.acknowledged_by = request.user
        else:
            return error_payload("Unsupported alert action.")
        alert.save(update_fields=["status", "acknowledged_at", "acknowledged_by", "updated_at"])
        return Response(workspace_payload(DashboardAlertSerializer(alert).data, f"Alert {action}d."))


class DashboardNotificationListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        _sync_application_notifications(request.user)
        queryset = DashboardNotification.objects.filter(owner=request.user)
        if request.query_params.get("unread") in {"1", "true", "True"}:
            queryset = queryset.filter(is_read=False)
        return Response(workspace_payload(DashboardNotificationSerializer(queryset[:100], many=True).data))


class DashboardNotificationReadView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        notification = DashboardNotification.objects.filter(owner=request.user, pk=pk).first()
        if not notification:
            return error_payload("Notification not found.", status.HTTP_404_NOT_FOUND)
        notification.is_read = True
        notification.save(update_fields=["is_read"])
        return Response(workspace_payload(DashboardNotificationSerializer(notification).data, "Notification marked as read."))


class DashboardNotificationReadAllView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        DashboardNotification.objects.filter(owner=request.user, is_read=False).update(is_read=True)
        return Response(workspace_payload(None, "All notifications marked as read."))


def _sync_application_notifications(user):
    recent_apps = PartnerApplication.objects.order_by("-created_at")[:20]
    for application in recent_apps:
        display_name = application.display_name or application.application_number
        DashboardNotification.objects.update_or_create(
            owner=user,
            external_key=f"onboarding:{application.pk}",
            defaults={
                "kind": "ONBOARDING",
                "title": f"Partner application {application.application_number}",
                "message": f"{display_name} is {application.get_status_display()}.",
                "status": application.status,
                "route": f"/onboarding/{application.pk}",
                "entity_type": "PartnerApplication",
                "entity_id": str(application.pk),
            },
        )


class GlobalSearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        query = request.query_params.get("q", "").strip()
        if len(query) < 2:
            return Response(workspace_payload({"query": query, "results": []}))
        results = []

        def add(model_name, queryset, label_getter, subtitle_getter, route_getter, kind):
            for item in queryset[:6]:
                results.append({
                    "id": str(item.pk),
                    "type": model_name,
                    "kind": kind,
                    "label": label_getter(item),
                    "subtitle": subtitle_getter(item),
                    "route": route_getter(item),
                })

        add(
            "Partner",
            Partner.objects.filter(
                Q(partner_number__icontains=query) | Q(first_name__icontains=query) |
                Q(surname__icontains=query) | Q(company_name__icontains=query) |
                Q(email__icontains=query) | Q(identification_number__icontains=query)
            ).order_by("-created_at"),
            lambda p: p.display_name or p.partner_number,
            lambda p: f"Partner · {p.partner_number} · {p.get_status_display()}",
            lambda p: f"/partners/{p.pk}",
            "partner",
        )
        add(
            "PartnerApplication",
            PartnerApplication.objects.filter(
                Q(application_number__icontains=query) | Q(first_name__icontains=query) |
                Q(surname__icontains=query) | Q(company_name__icontains=query) |
                Q(email__icontains=query)
            ).order_by("-created_at"),
            lambda a: a.display_name or a.application_number,
            lambda a: f"Onboarding · {a.application_number} · {a.get_status_display()}",
            lambda a: f"/onboarding/{a.pk}",
            "onboarding",
        )
        add(
            "User",
            User.objects.filter(
                Q(username__icontains=query) | Q(email__icontains=query) |
                Q(first_name__icontains=query) | Q(last_name__icontains=query)
            ).order_by("-date_joined"),
            lambda u: f"{u.first_name} {u.last_name}".strip() or u.username,
            lambda u: f"User · {u.email} · {u.get_status_display()}",
            lambda u: "/user-management/users",
            "user",
        )
        add(
            "OLPolicy",
            OLPolicy.objects.filter(Q(policy_number__icontains=query)).order_by("-created_at"),
            lambda p: p.policy_number,
            lambda p: f"Ordinary Life policy · {p.status}",
            lambda p: "/ordinary-life/policies",
            "policy",
        )
        add(
            "GLScheme",
            GLScheme.objects.filter(Q(scheme_number__icontains=query)).order_by("-created_at"),
            lambda s: s.scheme_number,
            lambda s: f"Group Life scheme · {s.scheme_number}",
            lambda s: "/group-life/schemes",
            "scheme",
        )
        add(
            "GCScheme",
            GCScheme.objects.filter(Q(scheme_number__icontains=query)).order_by("-created_at"),
            lambda s: s.scheme_number,
            lambda s: f"Group Credit scheme · {s.scheme_number}",
            lambda s: "/group-credit/schemes",
            "scheme",
        )
        return Response(workspace_payload({"query": query, "results": results[:30]}))


class CurrencyPairListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        pairs = CurrencyPair.objects.filter(owner=request.user).prefetch_related("rates")
        return Response(workspace_payload(CurrencyPairSerializer(pairs, many=True).data))

    def post(self, request):
        base = str(request.data.get("baseCurrency", request.data.get("base_currency", ""))).upper().strip()
        quote = str(request.data.get("quoteCurrency", request.data.get("quote_currency", ""))).upper().strip()
        if len(base) != 3 or len(quote) != 3 or not base.isalpha() or not quote.isalpha() or base == quote:
            return error_payload("Currency codes must be distinct three-letter ISO codes.")
        pair, created = CurrencyPair.objects.get_or_create(
            owner=request.user,
            base_currency=base,
            quote_currency=quote,
            defaults={"target_rate": request.data.get("targetRate", request.data.get("target_rate"))},

        )
        if not created and ("targetRate" in request.data or "target_rate" in request.data):
            target_rate = request.data.get("targetRate", request.data.get("target_rate"))
            try:
                pair.target_rate = Decimal(str(target_rate)) if target_rate not in (None, "") else None
                pair.save(update_fields=["target_rate", "updated_at"])
            except (InvalidOperation, ValueError):
                return error_payload("Target rate must be numeric.")
        return Response(workspace_payload(CurrencyPairSerializer(pair).data, "Currency pair added."), status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CurrencyPairDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        pair = CurrencyPair.objects.filter(owner=request.user, pk=pk).first()
        if not pair:
            return error_payload("Currency pair not found.", status.HTTP_404_NOT_FOUND)
        pair.delete()
        return Response(workspace_payload(None, "Currency pair removed."), status=status.HTTP_204_NO_CONTENT)


class CurrencyRefreshView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        pairs = list(CurrencyPair.objects.filter(owner=request.user, is_active=True))
        refreshed = []
        errors = []
        for pair in pairs:
            try:
                rate, as_of = _fetch_currency_rate(pair.base_currency, pair.quote_currency)
                CurrencyRate.objects.create(pair=pair, rate=rate, as_of=as_of, provider="exchangerate-api")
                refreshed.append(str(pair.pk))
            except (requests.RequestException, KeyError, ValueError, InvalidOperation) as exc:
                errors.append({"pair": f"{pair.base_currency}/{pair.quote_currency}", "error": str(exc)})
        return Response(workspace_payload({"refreshed": refreshed, "errors": errors}, "Currency tracker refreshed."))


def _fetch_currency_rate(base, quote):
    response = requests.get(f"https://open.er-api.com/v6/latest/{base}", timeout=8)
    response.raise_for_status()
    payload = response.json()
    if payload.get("result") != "success" or quote not in payload.get("rates", {}):
        raise KeyError(f"No rate available for {base}/{quote}")
    as_of = payload.get("time_last_update_utc", "")[:16]
    date_value = timezone.datetime.strptime(as_of, "%a, %d %b %Y") if as_of else timezone.localdate()
    return Decimal(str(payload["rates"][quote])), date_value.date() if hasattr(date_value, "date") else date_value

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime

from apps.partners.models import Partner
from apps.partner_onboarding.models import PartnerApplication
from apps.users.models import User
from .serializers import DashboardOverviewSerializer


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
        notifications = self._get_notifications_data()

        # Get todos (mock data)
        todos = self._get_todos_data()

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
        
        # Count by status
        status_counts = Partner.objects.values('status').annotate(
            count=Count('id')
        )
        
        # Count pending applications
        pending_count = PartnerApplication.objects.filter(
            status='PENDING'
        ).count()
        
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

    def _get_notifications_data(self):
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

    def _get_todos_data(self):
        """Get todo items (mock data)"""
        return [
            {
                "id": "1",
                "text": "Review pending applications",
                "date": timezone.now().strftime("%d %b %Y"),
                "completed": False
            },
            {
                "id": "2",
                "text": "Process approved partners",
                "date": timezone.now().strftime("%d %b %Y"),
                "completed": False
            }
        ]

    def _get_leads_data(self):
        """Get top leads (mock data)"""
        return [
            {"rank": 1, "name": "Partner Portal", "amount": "312.2M", "trophy": "🏆"},
            {"rank": 2, "name": "Corporate Sales", "amount": "259.5M", "trophy": "🥈"},
            {"rank": 3, "name": "Agency Network", "amount": "137.1M", "trophy": "🥉"}
        ]

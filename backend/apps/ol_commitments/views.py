from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.common.models import DomainEvent
from apps.ol_commitments.events import COMMITMENT_OVERDUE
from apps.ol_commitments.permissions import has_ol_commitment_permission
from apps.ol_commitments.services.overdue_service import lapse_review_rows, run_overdue_processing


class MustProcessOverduePermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_commitment_permission(request.user, "process_overdue")


class MustViewCommitmentsPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return has_ol_commitment_permission(request.user, "view")


class ProcessOverdueView(APIView):
    """POST /api/v1/ol-commitments/commitments/process-overdue/"""

    permission_classes = [MustProcessOverduePermission]

    def post(self, request):
        from apps.governance.services.audit_service import AuditContext

        result = run_overdue_processing(
            actor=AuditContext.get_context().get("user"),
            source_channel="BATCH",
        )
        return Response(
            {
                "data": {
                    "processed": result.processed,
                    "overdue": result.overdue,
                    "notified": result.notified,
                    "lapse_reviews": result.lapse_reviews,
                }
            }
        )


class LapseReviewView(APIView):
    """GET /api/v1/ol-commitments/commitments/lapse-review/"""

    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        return Response({"data": {"results": lapse_review_rows()}})


class OverdueNotificationsView(APIView):
    """GET /api/v1/ol-commitments/notifications/overdue/"""

    permission_classes = [MustViewCommitmentsPermission]

    def get(self, request):
        events = DomainEvent.objects.filter(event_type=COMMITMENT_OVERDUE).order_by("-occurred_at")[:30]
        items = []
        for event in events:
            payload = event.payload or {}
            commitment_id = payload.get("commitment_id") or event.aggregate_id
            commitment_number = payload.get("commitment_number") or ""
            items.append(
                {
                    "id": str(event.pk),
                    "title": f"Commitment {commitment_number or commitment_id or ''} is overdue",
                    "message": "A commitment passed its grace date and needs attention.",
                    "deep_link": f"/ordinary-life/commitments/{commitment_id}" if commitment_id else "/ordinary-life/commitments",
                    "created_at": event.occurred_at,
                }
            )
        return Response({"data": {"results": items}})
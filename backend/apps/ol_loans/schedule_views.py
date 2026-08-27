from django.db.models import Sum
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import loan_not_found
from .models import OLLoan
from .serializers import OLLoanScheduleSerializer
from .views import MustViewOLLoansPermission


class OLLoanScheduleView(APIView):
    """Return a paginated, read-only contractual schedule for one OL Loan."""

    permission_classes = [MustViewOLLoansPermission]

    def get(self, request, loan_id):
        loan = OLLoan.objects.filter(pk=loan_id).first()
        if loan is None:
            raise loan_not_found(str(loan_id))

        try:
            page = max(1, int(request.query_params.get("page", 1)))
        except (TypeError, ValueError):
            page = 1
        try:
            page_size = min(100, max(1, int(request.query_params.get("page_size", 20))))
        except (TypeError, ValueError):
            page_size = 20

        schedules = loan.schedules.order_by("installment_number", "due_date")
        totals = schedules.aggregate(
            principal=Sum("principal_due"),
            interest=Sum("interest_due"),
            penalty=Sum("penalty_due"),
            paid=Sum("amount_paid"),
            balance=Sum("balance"),
        )
        total_scheduled = sum((totals.get(key) or 0) for key in ("principal", "interest", "penalty"))
        total = schedules.count()
        start = (page - 1) * page_size
        rows = schedules[start : start + page_size]
        return Response(
            {
                "data": {
                    "results": OLLoanScheduleSerializer(rows, many=True).data,
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                    "aggregates": {
                        "total_scheduled": f"{total_scheduled:.2f}",
                        "total_paid": f"{(totals.get('paid') or 0):.2f}",
                        "remaining_balance": f"{(totals.get('balance') or 0):.2f}",
                    },
                }
            }
        )

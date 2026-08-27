from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import loan_not_found
from .models import OLLoan
from .serializers import OLLoanInterestAccrualSerializer, OLLoanRepaymentSerializer
from .views import MustViewOLLoansPermission


class _LoanHistoryView(APIView):
    permission_classes = [MustViewOLLoansPermission]
    relation_name = ""
    serializer_class = None
    ordering = "-created_at"

    def get_queryset(self, loan):
        return getattr(loan, self.relation_name).order_by(self.ordering)

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

        queryset = self.get_queryset(loan)
        total = queryset.count()
        start = (page - 1) * page_size
        rows = queryset[start : start + page_size]
        return Response(
            {
                "data": {
                    "results": self.serializer_class(rows, many=True).data,
                    "count": total,
                    "page": page,
                    "page_size": page_size,
                    "next": page * page_size < total,
                    "previous": page > 1,
                }
            }
        )


class OLLoanRepaymentsView(_LoanHistoryView):
    relation_name = "repayments"
    serializer_class = OLLoanRepaymentSerializer
    ordering = "-created_at"

    def get_queryset(self, loan):
        return loan.repayments.select_related("receipt_allocation__receipt").order_by(self.ordering)


class OLLoanAccrualsView(_LoanHistoryView):
    relation_name = "interest_accruals"
    serializer_class = OLLoanInterestAccrualSerializer
    ordering = "-period_end"

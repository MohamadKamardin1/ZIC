from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import loan_not_found
from .services.accrual_service import balance_for_loan
from .views import MustViewOLLoansPermission
from .models import OLLoan


class OLLoanBalanceView(APIView):
    permission_classes = [MustViewOLLoansPermission]

    def get(self, request, loan_id):
        loan = (
            OLLoan.objects.prefetch_related("interest_accruals", "repayments")
            .filter(pk=loan_id)
            .first()
        )
        if loan is None:
            raise loan_not_found(str(loan_id))
        return Response({"data": balance_for_loan(loan)})

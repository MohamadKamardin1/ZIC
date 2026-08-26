from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import not_found
from .models import Policy, PolicyLoan, WithdrawalRequest
from .permissions import HasOLPolicyPermission
from .serializers import PolicyLoanSerializer, WithdrawalRequestSerializer
from .services.finance_service import (
    approve_policy_loan,
    disburse_policy_loan,
    repay_policy_loan,
    request_policy_loan,
    request_policy_withdrawal,
)


class PolicyLoanListCreateView(APIView):
    permission_classes = [HasOLPolicyPermission]

    def get_permissions(self):
        self.action = "service" if self.request.method == "POST" else "retrieve"
        return super().get_permissions()

    def get(self, request, policy_id):
        if not Policy.objects.filter(pk=policy_id).exists():
            raise not_found(policy_id)
        loans = PolicyLoan.objects.filter(policy_id=policy_id).prefetch_related("repayments")
        return Response({"data": PolicyLoanSerializer(loans, many=True).data})

    def post(self, request, policy_id):
        loan = request_policy_loan(
            policy_id,
            amount=request.data.get("amount"),
            reason=request.data.get("reason", ""),
            as_of=request.data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": PolicyLoanSerializer(loan).data}, status=201)


class PolicyLoanApproveView(APIView):
    action = "service"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, loan_id):
        loan = approve_policy_loan(
            loan_id,
            as_of=request.data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": PolicyLoanSerializer(loan).data})


class PolicyLoanDisburseView(APIView):
    action = "service"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, loan_id):
        loan = disburse_policy_loan(
            loan_id,
            as_of=request.data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": PolicyLoanSerializer(loan).data})


class PolicyLoanRepayView(APIView):
    action = "service"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, loan_id):
        repayment = repay_policy_loan(
            loan_id,
            amount=request.data.get("amount"),
            payment_date=request.data.get("payment_date"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": repayment.loan and PolicyLoanSerializer(repayment.loan).data})


class PolicyWithdrawalListCreateView(APIView):
    permission_classes = [HasOLPolicyPermission]

    def get_permissions(self):
        self.action = "service" if self.request.method == "POST" else "retrieve"
        return super().get_permissions()

    def get(self, request, policy_id):
        if not Policy.objects.filter(pk=policy_id).exists():
            raise not_found(policy_id)
        withdrawals = WithdrawalRequest.objects.filter(policy_id=policy_id).order_by("-request_date", "-created_at")
        return Response({"data": WithdrawalRequestSerializer(withdrawals, many=True).data})

    def post(self, request, policy_id):
        withdrawal = request_policy_withdrawal(
            policy_id,
            amount=request.data.get("amount"),
            reason=request.data.get("reason", ""),
            as_of=request.data.get("as_of"),
            actor=request.user,
            request=request,
            source_channel="API",
        )
        return Response({"data": WithdrawalRequestSerializer(withdrawal).data}, status=201)

from django.urls import path

from .document_views import PolicyContractPrintView, PolicySchedulePrintView
from .endorsement_views import PolicyEndorsementDetailView, PolicyEndorsementListCreateView
from .finance_views import (
    PolicyLoanApproveView,
    PolicyLoanDisburseView,
    PolicyLoanListCreateView,
    PolicyLoanRepayView,
    PolicyWithdrawalListCreateView,
)
from .integration_views import (
    PolicyClaimRegistrationDataView,
    PolicyClaimSettledWebhookView,
    PolicyDashboardHooksView,
    PolicyPortalDetailView,
    PolicyPortalListView,
    PolicyReinsuranceRiskView,
)
from .issuance_views import PolicyIssueView
from .lifecycle_views import PolicyReinstateView
from .maturity_views import PolicyMaturityApproveView, PolicyMaturityPayView, PolicyMaturityView
from apps.ol_loans.request_views import PolicyLoanEligibilityView, PolicyLoanRequestView
from .termination_views import PolicyCancelView, PolicyPaidUpView, PolicySurrenderView
from .views import PolicyDetailView, PolicyExportView, PolicyKPIsView, PolicyListView

app_name = "ol_policies"

urlpatterns = [
    path("policies/issue/", PolicyIssueView.as_view(), name="policy-issue"),
    path("policies/kpis/", PolicyKPIsView.as_view(), name="policy-kpis"),
    path("policies/export/", PolicyExportView.as_view(), name="policy-export"),
    path("policies/<uuid:policy_id>/reinstate/", PolicyReinstateView.as_view(), name="policy-reinstate"),
    path("policies/<uuid:policy_id>/surrender/", PolicySurrenderView.as_view(), name="policy-surrender"),
    path("policies/<uuid:policy_id>/paid-up/", PolicyPaidUpView.as_view(), name="policy-paid-up"),
    path("policies/<uuid:policy_id>/cancel/", PolicyCancelView.as_view(), name="policy-cancel"),
    path("policies/<uuid:policy_id>/loans/eligibility/", PolicyLoanEligibilityView.as_view(), name="policy-loan-eligibility"),
    path("policies/<uuid:policy_id>/loans/request/", PolicyLoanRequestView.as_view(), name="policy-loan-request"),
    path("policies/<uuid:policy_id>/loans/", PolicyLoanListCreateView.as_view(), name="policy-loans"),
    path("policies/loans/<uuid:loan_id>/approve/", PolicyLoanApproveView.as_view(), name="policy-loan-approve"),
    path("policies/loans/<uuid:loan_id>/disburse/", PolicyLoanDisburseView.as_view(), name="policy-loan-disburse"),
    path("policies/loans/<uuid:loan_id>/repay/", PolicyLoanRepayView.as_view(), name="policy-loan-repay"),
    path("policies/<uuid:policy_id>/withdrawals/", PolicyWithdrawalListCreateView.as_view(), name="policy-withdrawals"),
    path("policies/<uuid:policy_id>/maturity/", PolicyMaturityView.as_view(), name="policy-maturity"),
    path("policies/<uuid:policy_id>/print-contract/", PolicyContractPrintView.as_view(), name="policy-print-contract"),
    path("policies/<uuid:policy_id>/print-schedule/", PolicySchedulePrintView.as_view(), name="policy-print-schedule"),
    path("policies/maturity/<uuid:claim_id>/approve/", PolicyMaturityApproveView.as_view(), name="policy-maturity-approve"),
    path("policies/maturity/<uuid:claim_id>/pay/", PolicyMaturityPayView.as_view(), name="policy-maturity-pay"),
    path("policies/<uuid:policy_id>/claim-data/", PolicyClaimRegistrationDataView.as_view(), name="policy-claim-data"),
    path("policies/<uuid:policy_id>/reinsurance-risk/", PolicyReinsuranceRiskView.as_view(), name="policy-reinsurance-risk"),
    path("policies/integrations/claim-settled/", PolicyClaimSettledWebhookView.as_view(), name="policy-claim-settled"),
    path("policies/portal/", PolicyPortalListView.as_view(), name="policy-portal-list"),
    path("policies/portal/<uuid:policy_id>/", PolicyPortalDetailView.as_view(), name="policy-portal-detail"),
    path("policies/dashboard-hooks/", PolicyDashboardHooksView.as_view(), name="policy-dashboard-hooks"),
    path("policies/", PolicyListView.as_view(), name="policy-list"),
    path(
        "policies/<uuid:policy_id>/endorsements/<uuid:endorsement_id>/",
        PolicyEndorsementDetailView.as_view(),
        name="policy-endorsement-detail",
    ),
    path(
        "policies/<uuid:policy_id>/endorsements/",
        PolicyEndorsementListCreateView.as_view(),
        name="policy-endorsement-list-create",
    ),
    path("policies/<uuid:policy_id>/", PolicyDetailView.as_view(), name="policy-detail"),
]

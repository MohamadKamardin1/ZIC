from django.urls import path

from .endorsement_views import PolicyEndorsementDetailView, PolicyEndorsementListCreateView
from .finance_views import (
    PolicyLoanApproveView,
    PolicyLoanDisburseView,
    PolicyLoanListCreateView,
    PolicyLoanRepayView,
    PolicyWithdrawalListCreateView,
)
from .issuance_views import PolicyIssueView
from .lifecycle_views import PolicyReinstateView
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
    path("policies/<uuid:policy_id>/loans/", PolicyLoanListCreateView.as_view(), name="policy-loans"),
    path("policies/loans/<uuid:loan_id>/approve/", PolicyLoanApproveView.as_view(), name="policy-loan-approve"),
    path("policies/loans/<uuid:loan_id>/disburse/", PolicyLoanDisburseView.as_view(), name="policy-loan-disburse"),
    path("policies/loans/<uuid:loan_id>/repay/", PolicyLoanRepayView.as_view(), name="policy-loan-repay"),
    path("policies/<uuid:policy_id>/withdrawals/", PolicyWithdrawalListCreateView.as_view(), name="policy-withdrawals"),
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

import os

urls_code = """
from apps.ordinary_life.views import (
    OLProductViewSet,
    OLClientViewSet,
    OLQuotationViewSet,
    OLProposalViewSet,
    OLCommitmentViewSet,
    OLPolicyViewSet,
    OLLoanViewSet,
    OLWithdrawalViewSet,
    OLClaimViewSet,
    OLMaturityInstallmentViewSet,
)

router.register(r"products", OLProductViewSet, basename="ol-product")
router.register(r"clients", OLClientViewSet, basename="ol-client")
router.register(r"quotations", OLQuotationViewSet, basename="ol-quotation")
router.register(r"proposals", OLProposalViewSet, basename="ol-proposal")
router.register(r"commitments", OLCommitmentViewSet, basename="ol-commitment")
router.register(r"policies", OLPolicyViewSet, basename="ol-policy")
router.register(r"loans", OLLoanViewSet, basename="ol-loan")
router.register(r"withdrawals", OLWithdrawalViewSet, basename="ol-withdrawal")
router.register(r"claims", OLClaimViewSet, basename="ol-claim")
router.register(r"maturity-installments", OLMaturityInstallmentViewSet, basename="ol-maturity-installment")
"""

with open("backend/apps/ordinary_life/urls.py", "a") as f:
    f.write(urls_code)

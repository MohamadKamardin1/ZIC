from rest_framework.response import Response
from rest_framework.views import APIView

from .permissions import HasOLLoanPermission
from .services.integration_service import loan_dashboard_hooks


class OLLoanDashboardHooksView(APIView):
    permission_classes = [HasOLLoanPermission]
    action = "view"

    def get(self, request):
        return Response({"success": True, "data": loan_dashboard_hooks()})

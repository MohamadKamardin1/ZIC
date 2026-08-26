from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.services.engine import DocumentEngine, DocumentEngineError

from .errors import not_found
from .models import Policy
from .permissions import HasOLPolicyPermission


def _failure(exc):
    payload = {
        "success": False,
        "status_code": exc.status_code,
        "message": str(exc),
        "error": str(exc),
        "code": exc.code,
    }
    if exc.resolution_steps:
        payload["resolution_steps"] = exc.resolution_steps
    return Response(payload, status=exc.status_code)


def _render_response(request, document_type, policy_id):
    try:
        instance = DocumentEngine.render(
            document_type=document_type,
            object_id=policy_id,
            actor=request.user,
            request=request,
        )
        payload = DocumentEngine.payload(instance, request=request, actor=request.user, signed=True)
        return Response(
            {
                "success": True,
                "status_code": 201,
                "message": "Policy document rendered successfully.",
                "data": {
                    **payload,
                    "instance": payload,
                    "preview_blob_base64_or_url": payload["preview_url"],
                    "signed_download_url": payload["signed_download_url"],
                },
            },
            status=201,
        )
    except DocumentEngineError as exc:
        return _failure(exc)


class PolicyContractPrintView(APIView):
    action = "print"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, policy_id):
        if not Policy.objects.filter(pk=policy_id).exists():
            raise not_found(policy_id)
        return _render_response(request, "POLICY_CONTRACT", policy_id)


class PolicySchedulePrintView(APIView):
    action = "print"
    permission_classes = [HasOLPolicyPermission]

    def post(self, request, policy_id):
        if not Policy.objects.filter(pk=policy_id).exists():
            raise not_found(policy_id)
        return _render_response(request, "POLICY_SCHEDULE", policy_id)

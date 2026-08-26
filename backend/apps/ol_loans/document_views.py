from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework.views import APIView

from apps.documents.services.engine import DocumentEngine, DocumentEngineError

from .permissions import has_ol_loan_permission


def _success(data, message, status_code=201):
    return Response(
        {
            "success": True,
            "status_code": status_code,
            "message": message,
            "data": data,
        },
        status=status_code,
    )


def _failure(message, status_code, code="DOCUMENT_ERROR", resolution_steps=None):
    payload = {
        "success": False,
        "status_code": status_code,
        "error_code": code,
        "code": code,
        "message": message,
        "error": message,
        "resolution_steps": resolution_steps or [],
    }
    return Response(payload, status=status_code)


class MustPrintOLLoanPermission(IsAuthenticated):
    def has_permission(self, request, view):
        return bool(super().has_permission(request, view) and has_ol_loan_permission(request.user, "print"))


class OLLoanDocumentPrintView(APIView):
    authentication_classes = api_settings.DEFAULT_AUTHENTICATION_CLASSES
    permission_classes = [MustPrintOLLoanPermission]
    document_type = ""

    def post(self, request, loan_id):
        try:
            instance = DocumentEngine.render(
                document_type=self.document_type,
                object_id=loan_id,
                actor=request.user,
                request=request,
            )
            payload = DocumentEngine.payload(instance, request=request, actor=request.user, signed=True)
            return _success(
                {
                    **payload,
                    "instance": payload,
                    "preview_blob_base64_or_url": payload["preview_url"],
                    "signed_download_url": payload["signed_download_url"],
                },
                "Loan document rendered successfully.",
            )
        except DocumentEngineError as exc:
            return _failure(str(exc), exc.status_code, code=exc.code, resolution_steps=exc.resolution_steps)


class OLLoanAgreementPrintView(OLLoanDocumentPrintView):
    document_type = "OL_LOAN_AGREEMENT"


class OLLoanSchedulePrintView(OLLoanDocumentPrintView):
    document_type = "OL_LOAN_SCHEDULE"

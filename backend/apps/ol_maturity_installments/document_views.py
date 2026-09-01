from rest_framework.response import Response
from rest_framework.views import APIView

from apps.documents.services.engine import DocumentEngine, DocumentEngineError

from .permissions import HasOLMaturityInstallmentPermission


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


class OLMaturityInstallmentDocumentPrintView(APIView):
    permission_classes = [HasOLMaturityInstallmentPermission]
    action = "print"
    document_type = ""

    def post(self, request, plan_id):
        try:
            instance = DocumentEngine.render(
                document_type=self.document_type,
                object_id=plan_id,
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
                "Maturity installment document rendered successfully.",
            )
        except DocumentEngineError as exc:
            return _failure(str(exc), exc.status_code, code=exc.code, resolution_steps=exc.resolution_steps)


class OLMaturitySchedulePrintView(OLMaturityInstallmentDocumentPrintView):
    document_type = "OL_MATURITY_SCHEDULE"


class OLMaturityPaymentAdvicePrintView(OLMaturityInstallmentDocumentPrintView):
    document_type = "OL_MATURITY_PAYMENT_ADVICE"

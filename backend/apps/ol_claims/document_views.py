from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import not_found
from .models import ClaimSourceChannel, OLClaim
from .permissions import HasOLClaimPermission
from .serializers import OLClaimDocumentSerializer
from .services.document_service import can_proceed_to_assessment, document_requirement_status, upload_document


def _claim(claim_id):
    claim = OLClaim.objects.select_related("policy_ref").filter(pk=claim_id).first()
    if not claim:
        raise not_found()
    return claim


def _source_channel(request):
    requested = str(request.META.get("HTTP_X_SOURCE_CHANNEL", "API")).strip().upper()
    return requested if requested in ClaimSourceChannel.values else ClaimSourceChannel.API


class ClaimDocumentsView(APIView):
    """List and upload claim evidence, keeping mandatory state explicit."""

    def get_permissions(self):
        self.action = "view" if self.request.method == "GET" else "register"
        return [HasOLClaimPermission()]

    def get(self, request, claim_id):
        claim = _claim(claim_id)
        requirement = document_requirement_status(claim)
        required = set(requirement["required_document_types"])
        uploaded = set(requirement["uploaded_document_types"])
        rows = list(claim.documents.order_by("document_type", "-upload_date"))
        return Response(
            {
                "data": {
                    "claim_number": claim.claim_number,
                    "results": OLClaimDocumentSerializer(rows, many=True).data,
                    "documents": OLClaimDocumentSerializer(rows, many=True).data,
                    "required_document_types": requirement["required_document_types"],
                    "missing_document_types": requirement["missing_document_types"],
                    "all_mandatory_uploaded": requirement["all_mandatory_uploaded"],
                    "mandatory": len(required),
                    "uploaded": len(required.intersection(uploaded)),
                    "requirements": [
                        {
                            "document_type": document_type,
                            "mandatory": True,
                            "uploaded": document_type in uploaded,
                        }
                        for document_type in requirement["required_document_types"]
                    ],
                }
            }
        )

    def post(self, request, claim_id):
        claim = _claim(claim_id)
        document, created = upload_document(
            claim=claim,
            document_type=request.data.get("document_type"),
            uploaded_file=request.FILES.get("file"),
            file_reference=request.data.get("file_reference", ""),
            actor=request.user,
            source_channel=_source_channel(request),
            request=request,
        )
        requirement = document_requirement_status(claim)
        return Response(
            {
                "data": {
                    "document": OLClaimDocumentSerializer(document).data,
                    "created": created,
                    "all_mandatory_uploaded": requirement["all_mandatory_uploaded"],
                    "missing_document_types": requirement["missing_document_types"],
                }
            },
            status=201 if created else 200,
        )


class ClaimAssessmentReadinessView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "assess"

    def get(self, request, claim_id):
        claim = _claim(claim_id)
        requirement = document_requirement_status(claim)
        return Response({"data": {"claim_number": claim.claim_number, "can_proceed_to_assessment": not requirement["missing_document_types"], **requirement}})

    def post(self, request, claim_id):
        can_proceed_to_assessment(claim_id, actor=request.user, source_channel=_source_channel(request))
        claim = _claim(claim_id)
        return Response(
            {
                "data": {
                    "claim_number": claim.claim_number,
                    "can_proceed_to_assessment": True,
                    "message": "All mandatory claim documents are present; assessment may proceed.",
                }
            }
        )

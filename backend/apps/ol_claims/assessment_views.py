from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from .errors import ClaimError, not_found
from .models import ClaimSourceChannel
from .permissions import HasOLClaimPermission
from .serializers import OLClaimDetailSerializer, OLClaimFileNoteSerializer
from .services.assessment import add_file_note, assess_claim
from .views import _base_queryset


def _source_channel(request):
    requested = str(request.META.get("HTTP_X_SOURCE_CHANNEL", "API")).strip().upper()
    return requested if requested in ClaimSourceChannel.values else ClaimSourceChannel.API


def _claim(claim_id):
    claim = _base_queryset().filter(pk=claim_id).first()
    if not claim:
        raise not_found()
    return claim


class ClaimAssessmentInputSerializer(serializers.Serializer):
    assessed_amount = serializers.DecimalField(max_digits=18, decimal_places=2, required=True)
    assessment_notes = serializers.CharField(required=True, allow_blank=False)
    fraud_flag = serializers.BooleanField(required=False, default=False)
    fraud_flag_reason = serializers.CharField(required=False, allow_blank=True, default="")
    waiver_of_premium_days = serializers.IntegerField(required=False, min_value=0, default=0)


class ClaimAssessmentView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "assess"

    def post(self, request, claim_id):
        serializer = ClaimAssessmentInputSerializer(data=request.data)
        if not serializer.is_valid():
            raise ClaimError(
                message="The assessment form needs correction before it can be saved.",
                error_code="CLAIM_ASSESSMENT_REQUIRED",
                status_code=400,
                field_errors=serializer.errors,
                resolution_steps=[
                    "Enter the assessed amount and assessment findings.",
                    "Confirm medical review and mandatory documents are complete.",
                    "Correct the highlighted fields and submit the assessment again.",
                ],
            )
        claim = assess_claim(
            claim_id,
            actor=request.user,
            request=request,
            source_channel=_source_channel(request),
            **serializer.validated_data,
        )
        return Response({"data": OLClaimDetailSerializer(claim).data})


class ClaimNotesView(APIView):
    permission_classes = [HasOLClaimPermission]
    action = "assess"

    def get(self, request, claim_id):
        claim = _claim(claim_id)
        return Response({"data": OLClaimFileNoteSerializer(claim.file_notes.all(), many=True).data})

    def post(self, request, claim_id):
        note = add_file_note(
            claim_id,
            note_text=request.data.get("note_text"),
            actor=request.user,
            request=request,
            source_channel=_source_channel(request),
        )
        return Response({"data": OLClaimFileNoteSerializer(note).data}, status=201)

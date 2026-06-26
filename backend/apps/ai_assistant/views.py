import logging
import re

from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.utils import timezone

from apps.partner_onboarding.services import ApplicationService
from apps.partner_onboarding.serializers import (
    PartnerApplicationCreateSerializer,
    PartnerApplicationDetailSerializer,
)

from .serializers import (
    AnalyzePromptSerializer,
    ExecutePartnerDataSerializer,
    ClarificationSerializer,
)
from .services import DeepSeekService

logger = logging.getLogger(__name__)


def _camel_to_snake(name: str) -> str:
    s = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s)
    return s.lower()


def _convert_keys(d: dict) -> dict:
    return {_camel_to_snake(k): v for k, v in d.items()}


def _envelope(data=None, message="", status_code=200):
    return Response(
        {
            "success": status_code < 400,
            "status_code": status_code,
            "message": message,
            "data": data,
            "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"},
        },
        status=status_code,
    )


@api_view(["POST"])
def analyze_prompt(request):
    serializer = AnalyzePromptSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    prompt = serializer.validated_data["prompt"]

    try:
        result = DeepSeekService.analyze_partner_prompt(prompt)
    except RuntimeError as e:
        return _envelope(message=str(e), status_code=503)

    missing_required = result.get("missing_required", [])
    missing_optional = result.get("missing_optional", [])

    explanation = DeepSeekService.explain_missing_fields(missing_required, missing_optional)

    return _envelope(
        message="Additional information needed." if missing_required else "Partner data analyzed successfully.",
        data={
            "status": "needs_clarification" if missing_required else "ready",
            "partnerType": result.get("partner_type"),
            "partnerData": result.get("partner_data", {}),
            "missingRequired": missing_required,
            "missingOptional": missing_optional,
            "explanation": explanation,
        },
    )


@api_view(["POST"])
def execute_partner_creation(request):
    serializer = ExecutePartnerDataSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    partner_type = serializer.validated_data["partner_type"]
    partner_data = _convert_keys(serializer.validated_data["partner_data"])

    partner_data["partner_type"] = partner_type
    partner_data = {k: v for k, v in partner_data.items() if v is not None}

    create_serializer = PartnerApplicationCreateSerializer(data=partner_data)
    create_serializer.is_valid(raise_exception=True)

    try:
        application = ApplicationService.create_draft(
            request.user, create_serializer.validated_data,
        )
    except Exception as e:
        logger.error(f"AI partner creation failed: {e}")
        return _envelope(message=f"Failed to create partner: {e}", status_code=400)

    return _envelope(
        message="Partner draft created successfully.",
        data=PartnerApplicationDetailSerializer(application).data,
        status_code=201,
    )


@api_view(["POST"])
def clarification_response(request):
    serializer = ClarificationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    prompt = serializer.validated_data["prompt"]
    missing_fields = serializer.validated_data.get("missing_fields", [])
    partial_data = serializer.validated_data.get("partial_data", {})

    try:
        result = DeepSeekService.clarify_partner_data(prompt, partial_data, missing_fields)
    except RuntimeError as e:
        return _envelope(message=str(e), status_code=503)

    missing_required = result.get("missing_required", [])
    missing_optional = result.get("missing_optional", [])

    explanation = DeepSeekService.explain_missing_fields(missing_required, missing_optional)

    return _envelope(
        message="Clarification processed.",
        data={
            "status": "ready" if not missing_required else "needs_clarification",
            "partnerType": result.get("partner_type"),
            "partnerData": result.get("partner_data", {}),
            "missingRequired": missing_required,
            "missingOptional": missing_optional,
            "explanation": explanation,
        },
    )

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.pagination import StandardPagination
from apps.core.permissions import IsAdminUser
from apps.partners.filters import PartnerFilter
from apps.partners.models import (
    CorporateProfile,
    IndividualProfile,
    Partner,
    PartnerAssignmentBankAccount,
    PartnerAssignmentContact,
    PartnerDocument,
    PartnerDynamicFieldValue,
    PartnerKYCProfile,
    PartnerType,
    PartnerTypeAssignment,
    PartnerTypeBankRequirement,
    PartnerTypeContactRequirement,
    PartnerTypeDocumentRequirement,
    PartnerTypeFieldConfiguration,
    UserPartnerLink,
)
from apps.partners.serializers import (
    CorporateProfileSerializer,
    IndividualProfileSerializer,
    PartnerAssignmentBankAccountSerializer,
    PartnerAssignmentContactSerializer,
    PartnerContextSerializer,
    PartnerDetailSerializer,
    PartnerDocumentSerializer,
    PartnerDynamicFieldValueSerializer,
    PartnerKYCProfileSerializer,
    PartnerListSerializer,
    PartnerTypeAssignmentCreateSerializer,
    PartnerTypeAssignmentHistorySerializer,
    PartnerTypeAssignmentSerializer,
    PartnerTypeAssignmentSetupSerializer,
    PartnerTypeBankRequirementSerializer,
    PartnerTypeContactRequirementSerializer,
    PartnerTypeDocumentRequirementSerializer,
    PartnerTypeFieldConfigurationSerializer,
    PartnerTypeSerializer,
    PartnerUpdateSerializer,
    UserPartnerLinkCreateSerializer,
    UserPartnerLinkRemoveSerializer,
    UserPartnerLinkSerializer,
)
from apps.partners.services.duplicate_detection import PartnerDuplicateDetectionService
from apps.partners.services.partner_link_service import PartnerLinkService
from apps.partners.services.partner_service import PartnerLifecycleService
from apps.partners.services.setup_service import PartnerSetupService

logger = logging.getLogger(__name__)


class PartnerReadAdminWriteMixin:
    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUser()]


def _response(data=None, message="", status_code=200):
    return Response({
        "success": status_code < 400,
        "status_code": status_code,
        "message": message,
        "data": data,
        "meta": {"timestamp": timezone.now().isoformat(), "version": "v1"},
    }, status=status_code)


class PartnerViewSet(viewsets.ModelViewSet):
    queryset = Partner.objects.select_related(
        "created_from_application",
    ).prefetch_related(
        "contacts", "bank_accounts",
        "individual_profile", "corporate_profile",
        "type_assignments__partner_type",
        "type_assignments__branch",
        "type_assignments__location",
    )
    pagination_class = StandardPagination
    filterset_class = PartnerFilter
    search_fields = [
        "partner_number", "first_name", "surname",
        "company_name", "email", "mobile_number",
    ]
    ordering_fields = [
        "created_at", "partner_number", "status", "partner_type",
    ]
    ordering = ["-created_at"]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user._has_partner_scope_bypass():
            return queryset
        return queryset.filter(pk__in=self.request.user.visible_partners().values("pk"))

    def get_serializer_class(self):
        if self.action == "list":
            return PartnerListSerializer
        if self.action in ("update", "partial_update"):
            return PartnerUpdateSerializer
        return PartnerDetailSerializer

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUser()]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(
            data=serializer.data,
            message="Partner retrieved successfully.",
        )

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(
            data=serializer.data,
            message="Partners retrieved successfully.",
        )

    def create(self, request, *args, **kwargs):
        return _response(
            message="Partners must be created via the onboarding conversion process.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    def destroy(self, request, *args, **kwargs):
        return _response(
            message="Partners cannot be deleted. Use deactivate instead.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=False, methods=["post"], url_path="check-duplicates")
    def check_duplicates(self, request):
        partner_type = request.data.get("partner_type", "")
        result = PartnerDuplicateDetectionService.comprehensive_check(
            partner_type=partner_type,
            **request.data,
        )
        return _response(
            data={
                "is_duplicate": result.is_duplicate,
                "matched_on": result.details.get("matched_on", []),
                "match_count": result.details.get("count", 0),
            },
            message="Duplicate check complete.",
        )

    @action(detail=True, methods=["post"], url_path="assign-type")
    def assign_partner_type(self, request, pk=None):
        partner = self.get_object()
        serializer = PartnerTypeAssignmentCreateSerializer(
            data=request.data,
            context={"partner": partner},
        )
        serializer.is_valid(raise_exception=True)
        assignment = serializer.save()
        return _response(
            data=PartnerTypeAssignmentSerializer(assignment).data,
            message=f"Partner type '{assignment.partner_type.name}' assigned.",
            status_code=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get", "patch"], url_path="individual-profile")
    def manage_individual_profile(self, request, pk=None):
        partner = self.get_object()
        try:
            profile = partner.individual_profile
        except IndividualProfile.DoesNotExist:
            profile = None

        if request.method == "GET":
            serializer = IndividualProfileSerializer(profile)
            return _response(data=serializer.data, message="Individual profile retrieved.")

        if profile is None:
            serializer = IndividualProfileSerializer(data=request.data)
        else:
            serializer = IndividualProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if profile is None:
            serializer.save(partner=partner)
        else:
            serializer.save()
        return _response(
            data=IndividualProfileSerializer(serializer.instance).data,
            message="Individual profile updated.",
        )

    @action(detail=True, methods=["get", "patch"], url_path="corporate-profile")
    def manage_corporate_profile(self, request, pk=None):
        partner = self.get_object()
        try:
            profile = partner.corporate_profile
        except CorporateProfile.DoesNotExist:
            profile = None

        if request.method == "GET":
            serializer = CorporateProfileSerializer(profile)
            return _response(data=serializer.data, message="Corporate profile retrieved.")

        if profile is None:
            serializer = CorporateProfileSerializer(data=request.data)
        else:
            serializer = CorporateProfileSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        if profile is None:
            serializer.save(partner=partner)
        else:
            serializer.save()
        return _response(
            data=CorporateProfileSerializer(serializer.instance).data,
            message="Corporate profile updated.",
        )

    @action(detail=True, methods=["get"], url_path="type-assignments")
    def list_type_assignments(self, request, pk=None):
        partner = self.get_object()
        assignments = partner.type_assignments.all().select_related(
            "partner_type", "branch", "location"
        )
        serializer = PartnerTypeAssignmentSerializer(assignments, many=True)
        return _response(data=serializer.data, message="Type assignments retrieved.")

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        partner = self.get_object()
        try:
            partner = PartnerLifecycleService.deactivate_partner(
                partner, request.data.get("reason", "")
            )
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            return _response(message=detail, status_code=status.HTTP_400_BAD_REQUEST)
        return _response(
            data=PartnerDetailSerializer(partner).data,
            message=f"Partner {partner.partner_number} deactivated.",
        )

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        partner = self.get_object()
        try:
            partner = PartnerLifecycleService.activate_partner(partner)
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            return _response(message=detail, status_code=status.HTTP_400_BAD_REQUEST)
        return _response(
            data=PartnerDetailSerializer(partner).data,
            message=f"Partner {partner.partner_number} activated.",
        )


class UserPartnerLinkViewSet(viewsets.ModelViewSet):
    queryset = UserPartnerLink.objects.select_related("user", "partner", "created_by")
    serializer_class = UserPartnerLinkSerializer
    pagination_class = StandardPagination

    def get_permissions(self):
        if self.action == "my_context":
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUser()]

    def get_serializer_class(self):
        if self.action == "create":
            return UserPartnerLinkCreateSerializer
        if self.action == "deactivate":
            return UserPartnerLinkRemoveSerializer
        return UserPartnerLinkSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = PartnerLinkService.link_user(
            actor=request.user,
            user=serializer.validated_data["user"],
            partner=serializer.validated_data["partner"],
            data=serializer.validated_data,
            request=request,
        )
        return _response(
            data=UserPartnerLinkSerializer(link).data,
            message="User-partner link created.",
            status_code=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        return _response(
            message="User-partner links cannot be deleted. Use deactivate instead.",
            status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        )

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        link = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        link = PartnerLinkService.unlink_user(
            actor=request.user,
            link=link,
            request=request,
            reason=serializer.validated_data.get("reason", ""),
        )
        return _response(data=UserPartnerLinkSerializer(link).data, message="User-partner link deactivated.")

    @action(detail=True, methods=["post"], url_path="set-primary")
    def set_primary(self, request, pk=None):
        link = PartnerLinkService.set_primary(actor=request.user, link=self.get_object(), request=request)
        return _response(data=UserPartnerLinkSerializer(link).data, message="Primary partner changed.")

    @action(detail=False, methods=["get"], url_path="my-context")
    def my_context(self, request):
        visible = request.user.visible_partners()
        current = request.user.current_partner()
        return _response(
            data={
                "current_partner": PartnerContextSerializer(current).data if current else None,
                "partners": PartnerContextSerializer(visible, many=True).data,
                "partner_ids": [str(partner_id) for partner_id in visible.values_list("id", flat=True)],
                "partner_count": visible.count(),
            },
            message="Partner context retrieved.",
        )


class PartnerContextView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        visible = request.user.visible_partners()
        current = request.user.current_partner()
        return _response(
            data={
                "current_partner": PartnerContextSerializer(current).data if current else None,
                "partners": PartnerContextSerializer(visible, many=True).data,
                "partner_ids": [str(partner_id) for partner_id in visible.values_list("id", flat=True)],
                "partner_count": visible.count(),
            },
            message="Partner context retrieved.",
        )


class PartnerTypeViewSet(PartnerReadAdminWriteMixin, viewsets.ModelViewSet):
    queryset = PartnerType.objects.all().order_by("name")
    serializer_class = PartnerTypeSerializer
    pagination_class = StandardPagination
    search_fields = ["code", "name"]
    ordering_fields = ["name", "code", "created_at"]
    ordering = ["name"]

    def get_permissions(self):
        if self.action in ("list", "retrieve"):
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated(), IsAdminUser()]

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    def perform_create(self, serializer):
        instance = serializer.save()
        defaults = [
            PartnerTypeDocumentRequirement(
                partner_type=instance,
                code="IDENTITY_DOC",
                description="Identity Document",
                is_required=True,
                sort_order=1,
            ),
            PartnerTypeDocumentRequirement(
                partner_type=instance,
                code="PROOF_OF_ADDRESS",
                description="Proof of Address",
                is_required=True,
                sort_order=2,
            ),
        ]
        PartnerTypeDocumentRequirement.objects.bulk_create(defaults)


class PartnerTypeDocumentRequirementViewSet(PartnerReadAdminWriteMixin, viewsets.ModelViewSet):
    serializer_class = PartnerTypeDocumentRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["code", "description"]
    ordering_fields = ["partner_type", "sort_order", "code", "created_at"]
    ordering = ["partner_type", "sort_order", "code"]

    def get_queryset(self):
        qs = PartnerTypeDocumentRequirement.objects.select_related(
            "partner_type", "created_by", "updated_by",
        ).all()
        partner_type_pk = self.kwargs.get("partner_type_pk")
        if partner_type_pk:
            qs = qs.filter(partner_type_id=partner_type_pk)
        return qs

    def perform_create(self, serializer):
        partner_type_pk = self.kwargs.get("partner_type_pk")
        serializer.save(
            created_by=self.request.user,
            partner_type_id=partner_type_pk or serializer.validated_data.get("partner_type"),
        )

    def perform_update(self, serializer):
        serializer.save(updated_by=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(
            data=serializer.data,
            message="Document requirements retrieved successfully.",
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return _response(
            data=serializer.data,
            message="Document requirement created.",
            status_code=status.HTTP_201_CREATED,
        )

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(
            data=serializer.data,
            message="Document requirement retrieved.",
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return _response(
            data=serializer.data,
            message="Document requirement updated.",
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return _response(
            message="Document requirement deleted.",
            status_code=status.HTTP_200_OK,
        )


class PartnerTypeFieldConfigurationViewSet(PartnerReadAdminWriteMixin, viewsets.ModelViewSet):
    serializer_class = PartnerTypeFieldConfigurationSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["field_code", "field_name"]
    ordering_fields = ["partner_type", "display_order", "field_code", "created_at"]
    ordering = ["partner_type", "display_order", "field_code"]

    def get_queryset(self):
        qs = PartnerTypeFieldConfiguration.objects.select_related("partner_type").all()
        partner_type_pk = self.kwargs.get("partner_type_pk")
        if partner_type_pk:
            qs = qs.filter(partner_type_id=partner_type_pk)
        return qs

    def perform_create(self, serializer):
        partner_type_pk = self.kwargs.get("partner_type_pk")
        serializer.save(partner_type_id=partner_type_pk or serializer.validated_data.get("partner_type"))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Field configurations retrieved.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return _response(data=serializer.data, message="Field configuration created.", status_code=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Field configuration retrieved.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _response(data=serializer.data, message="Field configuration updated.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return _response(message="Field configuration deleted.", status_code=status.HTTP_200_OK)


class PartnerTypeContactRequirementViewSet(PartnerReadAdminWriteMixin, viewsets.ModelViewSet):
    serializer_class = PartnerTypeContactRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["contact_type"]
    ordering_fields = ["partner_type", "display_order", "contact_type", "created_at"]
    ordering = ["partner_type", "display_order", "contact_type"]

    def get_queryset(self):
        qs = PartnerTypeContactRequirement.objects.select_related("partner_type").all()
        partner_type_pk = self.kwargs.get("partner_type_pk")
        if partner_type_pk:
            qs = qs.filter(partner_type_id=partner_type_pk)
        return qs

    def perform_create(self, serializer):
        partner_type_pk = self.kwargs.get("partner_type_pk")
        serializer.save(partner_type_id=partner_type_pk or serializer.validated_data.get("partner_type"))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Contact requirements retrieved.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return _response(data=serializer.data, message="Contact requirement created.", status_code=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Contact requirement retrieved.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _response(data=serializer.data, message="Contact requirement updated.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return _response(message="Contact requirement deleted.", status_code=status.HTTP_200_OK)


class PartnerTypeBankRequirementViewSet(PartnerReadAdminWriteMixin, viewsets.ModelViewSet):
    serializer_class = PartnerTypeBankRequirementSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination
    search_fields = ["bank_type"]
    ordering_fields = ["partner_type", "display_order", "bank_type", "created_at"]
    ordering = ["partner_type", "display_order", "bank_type"]

    def get_queryset(self):
        qs = PartnerTypeBankRequirement.objects.select_related("partner_type").all()
        partner_type_pk = self.kwargs.get("partner_type_pk")
        if partner_type_pk:
            qs = qs.filter(partner_type_id=partner_type_pk)
        return qs

    def perform_create(self, serializer):
        partner_type_pk = self.kwargs.get("partner_type_pk")
        serializer.save(partner_type_id=partner_type_pk or serializer.validated_data.get("partner_type"))

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(queryset, many=True)
        return _response(data=serializer.data, message="Bank requirements retrieved.")

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return _response(data=serializer.data, message="Bank requirement created.", status_code=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return _response(data=serializer.data, message="Bank requirement retrieved.")

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop("partial", False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _response(data=serializer.data, message="Bank requirement updated.")

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return _response(message="Bank requirement deleted.", status_code=status.HTTP_200_OK)


class PartnerTypeAssignmentSetupViewSet(PartnerReadAdminWriteMixin, viewsets.GenericViewSet):
    serializer_class = PartnerTypeAssignmentSetupSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardPagination

    def get_queryset(self):
        return PartnerTypeAssignment.objects.select_related(
            "partner", "partner_type",
        ).prefetch_related(
            "documents__document_requirement",
            "field_values__field_config",
            "assignment_contacts__contact_requirement",
            "assignment_bank_accounts__bank_requirement",
            "kyc_profiles",
        ).all()

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        filter_kwargs = {self.lookup_field: self.kwargs.get(lookup_url_kwarg)}
        return get_object_or_404(queryset, **filter_kwargs)

    @action(detail=True, methods=["get"])
    def summary(self, request, pk=None):
        assignment = self.get_object()
        data = PartnerSetupService.get_setup_summary(assignment)
        return _response(data=data, message="Setup summary retrieved.")

    @action(detail=True, methods=["get", "post"], url_path="documents")
    def manage_documents(self, request, pk=None):
        assignment = self.get_object()
        if request.method == "GET":
            serializer = PartnerDocumentSerializer(assignment.documents.all(), many=True)
            return _response(data=serializer.data, message="Documents retrieved.")
        serializer = PartnerDocumentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(assignment=assignment)
        return _response(data=serializer.data, message="Document created.", status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "patch"], url_path="documents/(?P<document_pk>[^/.]+)")
    def manage_document_detail(self, request, pk=None, document_pk=None):
        assignment = self.get_object()
        document = get_object_or_404(PartnerDocument, id=document_pk, assignment=assignment)
        if request.method == "GET":
            serializer = PartnerDocumentSerializer(document)
            return _response(data=serializer.data, message="Document retrieved.")
        serializer = PartnerDocumentSerializer(document, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _response(data=serializer.data, message="Document updated.")

    @action(detail=True, methods=["get", "patch"], url_path="field-values")
    def manage_field_values(self, request, pk=None):
        assignment = self.get_object()
        if request.method == "GET":
            serializer = PartnerDynamicFieldValueSerializer(assignment.field_values.all(), many=True)
            return _response(data=serializer.data, message="Field values retrieved.")
        data = request.data
        if isinstance(data, list):
            results = []
            for item in data:
                fv, _ = PartnerDynamicFieldValue.objects.update_or_create(
                    assignment=assignment,
                    field_config_id=item.get("field_config"),
                    defaults={"value_json": item.get("value_json", {})},
                )
                results.append(PartnerDynamicFieldValueSerializer(fv).data)
            return _response(data=results, message="Field values updated.")
        serializer = PartnerDynamicFieldValueSerializer(
            assignment.field_values.all(), data=data, many=True, partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _response(data=serializer.data, message="Field values updated.")

    @action(detail=True, methods=["get", "post"], url_path="contacts")
    def manage_contacts(self, request, pk=None):
        assignment = self.get_object()
        if request.method == "GET":
            serializer = PartnerAssignmentContactSerializer(assignment.assignment_contacts.all(), many=True)
            return _response(data=serializer.data, message="Contacts retrieved.")
        serializer = PartnerAssignmentContactSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(assignment=assignment)
        return _response(data=serializer.data, message="Contact created.", status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "patch", "delete"], url_path="contacts/(?P<contact_pk>[^/.]+)")
    def manage_contact_detail(self, request, pk=None, contact_pk=None):
        assignment = self.get_object()
        contact = get_object_or_404(PartnerAssignmentContact, id=contact_pk, assignment=assignment)
        if request.method == "GET":
            serializer = PartnerAssignmentContactSerializer(contact)
            return _response(data=serializer.data, message="Contact retrieved.")
        if request.method == "DELETE":
            contact.delete()
            return _response(message="Contact deleted.")
        serializer = PartnerAssignmentContactSerializer(contact, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _response(data=serializer.data, message="Contact updated.")

    @action(detail=True, methods=["get", "post"], url_path="bank-accounts")
    def manage_bank_accounts(self, request, pk=None):
        assignment = self.get_object()
        if request.method == "GET":
            serializer = PartnerAssignmentBankAccountSerializer(
                assignment.assignment_bank_accounts.all(), many=True,
            )
            return _response(data=serializer.data, message="Bank accounts retrieved.")
        serializer = PartnerAssignmentBankAccountSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(assignment=assignment)
        return _response(data=serializer.data, message="Bank account created.", status_code=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get", "patch", "delete"], url_path="bank-accounts/(?P<bank_pk>[^/.]+)")
    def manage_bank_detail(self, request, pk=None, bank_pk=None):
        assignment = self.get_object()
        bank = get_object_or_404(PartnerAssignmentBankAccount, id=bank_pk, assignment=assignment)
        if request.method == "GET":
            serializer = PartnerAssignmentBankAccountSerializer(bank)
            return _response(data=serializer.data, message="Bank account retrieved.")
        if request.method == "DELETE":
            bank.delete()
            return _response(message="Bank account deleted.")
        serializer = PartnerAssignmentBankAccountSerializer(bank, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _response(data=serializer.data, message="Bank account updated.")

    @action(detail=True, methods=["get"], url_path="history")
    def history(self, request, pk=None):
        assignment = self.get_object()
        history = assignment.status_history.select_related("changed_by").all()
        return _response(
            data=PartnerTypeAssignmentHistorySerializer(history, many=True).data,
            message="Assignment history retrieved.",
        )

    @action(detail=True, methods=["post"], url_path="deactivate")
    def deactivate(self, request, pk=None):
        assignment = self.get_object()
        try:
            assignment = PartnerLifecycleService.deactivate_assignment(
                assignment, request.data.get("reason", "")
            )
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            return _response(message=detail, status_code=status.HTTP_400_BAD_REQUEST)
        return _response(
            data=PartnerTypeAssignmentSerializer(assignment).data,
            message="Partner type assignment deactivated.",
        )

    @action(detail=True, methods=["post"], url_path="activate")
    def activate(self, request, pk=None):
        assignment = self.get_object()
        try:
            assignment = PartnerLifecycleService.activate_assignment(
                assignment, request.data.get("reason", "")
            )
        except DjangoValidationError as exc:
            detail = exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            return _response(message=detail, status_code=status.HTTP_400_BAD_REQUEST)
        return _response(
            data=PartnerTypeAssignmentSerializer(assignment).data,
            message="Partner type assignment activated.",
        )

    @action(detail=True, methods=["get", "patch"], url_path="kyc")
    def manage_kyc(self, request, pk=None):
        assignment = self.get_object()
        kyc, _ = PartnerKYCProfile.objects.get_or_create(
            assignment=assignment,
            defaults={"kyc_status": "NOT_SET"},
        )
        if request.method == "GET":
            serializer = PartnerKYCProfileSerializer(kyc)
            return _response(data=serializer.data, message="KYC profile retrieved.")
        serializer = PartnerKYCProfileSerializer(kyc, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return _response(data=serializer.data, message="KYC profile updated.")

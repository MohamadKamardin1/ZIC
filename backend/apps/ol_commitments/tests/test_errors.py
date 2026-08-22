from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError
from django.test import RequestFactory, TestCase
from rest_framework import status
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.core.exceptions import ZICAPIException, custom_exception_handler
from apps.ol_commitments.errors import CommitmentError, parameter_missing

User = get_user_model()

REQUIRED_SHAPE_KEYS = ("error_code", "message", "resolution_steps", "field_errors", "doc_ref")


class StructuredErrorShapeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="shape_tester",
            password="Password@12345",
            email="shape_tester@zic.tz",
        )
        self.factory = RequestFactory()

    def _render(self, exc):
        request = self.factory.get("/api/v1/ol-commitments/")
        request.user = self.user
        request.request_id = "test-correlation-1"
        response = custom_exception_handler(exc, {"request": request, "view": None})
        self.assertIsNotNone(response)
        return response.data

    def test_commitment_error_renders_required_flat_shape(self):
        error = CommitmentError(
            "The payment amount exceeds the outstanding balance.",
            error_code="COMMITMENT_OVERPAYMENT",
            resolution_steps=["Adjust the amount.", "Review the outstanding balance."],
            field_errors={"amount": ["Cannot exceed balance."]},
        )
        data = self._render(error)
        for key in REQUIRED_SHAPE_KEYS:
            self.assertIn(key, data)
        self.assertIn("status_code", data)
        self.assertIn("success", data)
        self.assertIn("meta", data)
        self.assertEqual(data["error_code"], "COMMITMENT_OVERPAYMENT")
        self.assertEqual(data["message"], "The payment amount exceeds the outstanding balance.")
        self.assertEqual(data["resolution_steps"], ["Adjust the amount.", "Review the outstanding balance."])
        self.assertEqual(data["field_errors"], {"amount": ["Cannot exceed balance."]})
        self.assertEqual(data["doc_ref"], "docs/OL_COMMITMENTS_DESIGN.md")
        self.assertIs(data["success"], False)

    def test_parameter_missing_has_navigation_resolution(self):
        error = parameter_missing(
            "OL Grace Period",
            navigation_path="Ordinary Life Parameters > Policy Setup > OL Grace Period",
        )
        data = self._render(error)
        self.assertEqual(data["error_code"], "PARAMETER_MISSING")
        self.assertEqual(data["status_code"], 422)
        self.assertIn("Ordinary Life Parameters > Policy Setup > OL Grace Period", data["message"])
        self.assertTrue(any("OL Parameters" in step for step in data["resolution_steps"]))

    def test_zic_api_exception_keeps_legacy_envelope(self):
        error = ZICAPIException(
            "Quotation rejected",
            code="QUOTATION_REJECTED",
            status_code=409,
            details={"quote_number": "OLQ-1"},
        )
        data = self._render(error)
        self.assertEqual(data["error_code"], "QUOTATION_REJECTED")
        self.assertEqual(data["error"]["code"], "QUOTATION_REJECTED")
        self.assertEqual(data["error"]["details"], {"quote_number": "OLQ-1"})
        self.assertEqual(data["meta"]["request_id"], "test-correlation-1")

    def test_django_validation_error_maps_to_field_errors_shape(self):
        error = ValidationError({"status": ["Status must be configured."], "currency": ["Currency is required."]})
        data = self._render(error)
        self.assertEqual(data["status_code"], 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")
        self.assertEqual(data["field_errors"]["status"], ["Status must be configured."])
        self.assertEqual(data["field_errors"]["currency"], ["Currency is required."])

    def test_drf_validation_error_maps_to_field_errors_shape(self):
        error = DRFValidationError({"amount": ["Cannot exceed balance of 100000.00."]})
        data = self._render(error)
        self.assertEqual(data["status_code"], 400)
        self.assertEqual(data["error_code"], "VALIDATION_ERROR")
        self.assertEqual(data["field_errors"], {"amount": ["Cannot exceed balance of 100000.00."]})

    def test_permission_denied_maps_to_forbidden_shape(self):
        error = PermissionDenied("Missing permission: ol_commitments.waive")
        data = self._render(error)
        self.assertEqual(data["status_code"], 403)
        self.assertEqual(data["error_code"], "FORBIDDEN")
        self.assertIsInstance(data["resolution_steps"], list)
        self.assertEqual(data["doc_ref"], "docs/OL_COMMITMENTS_DESIGN.md")

    def test_not_found_maps_to_structured_shape(self):
        error = NotFound("Commitment not found.")
        data = self._render(error)
        self.assertEqual(data["status_code"], status.HTTP_404_NOT_FOUND)
        self.assertEqual(data["error_code"], "NOT_FOUND")
        self.assertEqual(data["message"], "Commitment not found.")

    def test_unhandled_exception_returns_internal_error_shape(self):
        error = RuntimeError("boom")
        data = self._render(error)
        self.assertEqual(data["status_code"], 500)
        self.assertEqual(data["error_code"], "INTERNAL_SERVER_ERROR")
        self.assertIsInstance(data["resolution_steps"], list)

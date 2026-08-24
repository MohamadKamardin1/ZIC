from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIRequestFactory

from apps.core.exceptions import custom_exception_handler
from apps.front_office.receipts.errors import (
    RECEIPT_ERROR_REGISTRY,
    ReceiptError,
    invalid_status,
    not_found,
    parameter_missing,
    permission_denied,
    raise_registry_error,
    registry_error,
)

User = get_user_model()


class ReceiptErrorRegistryTests(TestCase):
    REQUIRED_CODES = {
        "RECEIPT_NOT_FOUND",
        "RECEIPT_INVALID_STATUS",
        "RECEIPT_AMOUNT_INVALID",
        "RECEIPT_ALLOCATION_INVALID",
        "RECEIPT_OVERALLOCATION",
        "RECEIPT_ALREADY_POSTED",
        "RECEIPT_ALREADY_REVERSED",
        "RECEIPT_REASON_REQUIRED",
        "RECEIPT_REVERSAL_LOCKED",
        "RECEIPT_CURRENCY_MISMATCH",
        "RECEIPT_PERMISSION_DENIED",
        "RECEIPT_PARAMETER_MISSING",
    }

    def test_registry_contains_all_required_codes(self):
        self.assertTrue(self.REQUIRED_CODES.issubset(set(RECEIPT_ERROR_REGISTRY)))

    def test_registry_entries_have_shape(self):
        for code, (message, status_code, steps) in RECEIPT_ERROR_REGISTRY.items():
            self.assertTrue(message)
            self.assertIsInstance(status_code, int)
            self.assertIsInstance(steps, list)
            self.assertTrue(steps)

    def test_registry_error_returns_structured_exception(self):
        error = registry_error("RECEIPT_NOT_FOUND")
        self.assertIsInstance(error, ReceiptError)
        self.assertEqual(error.error_code, "RECEIPT_NOT_FOUND")
        self.assertEqual(error.status_code, 404)
        self.assertTrue(error.resolution_steps)

    def test_raise_registry_error(self):
        with self.assertRaises(ReceiptError) as ctx:
            raise_registry_error("RECEIPT_OVERALLOCATION")
        self.assertEqual(ctx.exception.error_code, "RECEIPT_OVERALLOCATION")
        self.assertEqual(ctx.exception.status_code, 422)

    def test_not_found_helper(self):
        error = not_found("RCT-2026-000001")
        self.assertEqual(error.error_code, "RECEIPT_NOT_FOUND")
        self.assertEqual(error.status_code, 404)

    def test_invalid_status_helper(self):
        error = invalid_status("update", "POSTED")
        self.assertEqual(error.error_code, "RECEIPT_INVALID_STATUS")
        self.assertEqual(error.status_code, 422)

    def test_permission_denied_helper(self):
        error = permission_denied("reverse")
        self.assertEqual(error.error_code, "RECEIPT_PERMISSION_DENIED")
        self.assertEqual(error.status_code, 403)

    def test_parameter_missing_helper(self):
        error = parameter_missing("RECEIPT_PAYMENT_MODES")
        self.assertEqual(error.error_code, "RECEIPT_PARAMETER_MISSING")
        self.assertEqual(error.status_code, 422)


class ReceiptErrorShapeTests(TestCase):
    def test_exception_handler_renders_structured_shape(self):
        factory = APIRequestFactory()
        request = factory.get("/api/v1/front-office/receipts/")
        request.request_id = "req-123"
        error = not_found()
        response = custom_exception_handler(error, {"request": request})
        self.assertEqual(response.status_code, 404)
        body = response.data
        self.assertFalse(body["success"])
        self.assertEqual(body["error_code"], "RECEIPT_NOT_FOUND")
        self.assertEqual(body["message"], "Receipt the requested receipt could not be found.")
        self.assertIsInstance(body["resolution_steps"], list)
        self.assertIsInstance(body["field_errors"], dict)
        self.assertEqual(body["doc_ref"], "docs/FRONT_OFFICE_RECEIPTS_DESIGN.md")
        self.assertEqual(body["error"]["code"], "RECEIPT_NOT_FOUND")
        self.assertEqual(body["meta"]["version"], "v1")

    def test_field_errors_are_preserved(self):
        from rest_framework.test import APIRequestFactory

        factory = APIRequestFactory()
        request = factory.get("/api/v1/front-office/receipts/")
        error = registry_error(
            "RECEIPT_AMOUNT_INVALID", field_errors={"receipt_amount": ["Amount must be greater than zero."]}
        )
        response = custom_exception_handler(error, {"request": request})
        self.assertEqual(response.data["field_errors"]["receipt_amount"], ["Amount must be greater than zero."])

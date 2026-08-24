from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from apps.core.exceptions import custom_exception_handler
from apps.ol_proposals.errors import (
    beneficiary_shares_invalid,
    first_premium_not_posted,
    invalid_transition,
    mandatory_documents_missing,
    parameter_missing,
    partner_not_verified,
)

User = get_user_model()

REQUIRED_KEYS = ("error_code", "message", "resolution_steps", "field_errors", "doc_ref")


class ProposalErrorShapeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="shape_probe", password="Password@12345", email="shape_probe@zic.tz")
        self.factory = RequestFactory()

    def _render(self, error):
        request = self.factory.get("/api/v1/ol-proposals/")
        request.user = self.user
        request.request_id = "proposal-correlation"
        response = custom_exception_handler(error, {"request": request, "view": None})
        return response.data

    def test_proposal_error_shapes(self):
        cases = [
            partner_not_verified("Asha"),
            beneficiary_shares_invalid(Decimal99()),
            mandatory_documents_missing(["Identity Card", "Proof of Address"]),
            first_premium_not_posted(),
            invalid_transition("convert", "ENRICHMENT", ["AWAITING_FIRST_PREMIUM"]),
            parameter_missing("OL Proposal Status", "OL Parameters > Policy Setup > OL Proposal Statuses"),
        ]
        for error in cases:
            data = self._render(error)
            for key in REQUIRED_KEYS:
                self.assertIn(key, data)
            self.assertIsInstance(data["resolution_steps"], list)
            self.assertTrue(data["error_code"].startswith("PROPOSAL_") or data["error_code"] == "PARAMETER_MISSING")

    def test_invalid_transition_lists_allowed_states(self):
        data = self._render(invalid_transition("convert", "ENRICHMENT", ["AWAITING_FIRST_PREMIUM", "CANCELLED"]))
        steps = " ".join(data["resolution_steps"])
        self.assertIn("AWAITING_FIRST_PREMIUM", steps)
        self.assertIn("CANCELLED", steps)

    def test_parameter_missing_has_navigation(self):
        data = self._render(parameter_missing("OL Proposal Status", "OL Parameters > Policy Setup > OL Proposal Statuses"))
        self.assertEqual(data["error_code"], "PARAMETER_MISSING")
        self.assertIn("OL Parameters", data["message"])


def Decimal99():
    from decimal import Decimal

    return Decimal("99.50")
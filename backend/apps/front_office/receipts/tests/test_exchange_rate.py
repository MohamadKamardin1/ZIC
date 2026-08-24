from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.front_office.receipts.models import ExchangeRate, ReceiptAllocation
from apps.governance.models import AuditLog
from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLCommitmentStatus
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner
from apps.system_parameters.models import ParameterGroup, SystemParameter

User = get_user_model()

BASE = "/api/v1/front-office/receipts"


def seed_commitment_statuses():
    for code, name, order, terminal in (
        ("PENDING", "Pending", 10, False),
        ("PARTIALLY_PAID", "Partially paid", 20, False),
        ("COMPLETED", "Completed", 30, True),
    ):
        OLCommitmentStatus.objects.update_or_create(
            code=code,
            defaults={"name": name, "applies_to": "COMMITMENT", "display_order": order, "is_terminal": terminal, "is_active": True},
        )


def make_partner(seq=1, **overrides):
    defaults = {
        "partner_number": f"FX{seq:04d}",
        "partner_type": "INDIVIDUAL",
        "party_type": "INDIVIDUAL",
        "first_name": "Jane",
        "surname": "Doe",
        "email": f"fx{seq}@zic.tz",
        "mobile_number": f"2557000000{seq}",
        "is_active": True,
        "status": "ACTIVE",
    }
    defaults.update(overrides)
    return Partner.objects.create(**defaults)


class ExchangeRateBehaviorTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        seed_commitment_statuses()
        self.admin = User.objects.create_superuser(
            username="fx_admin", password="Password@12345", email="fx_admin@zic.tz"
        )
        self.plain = User.objects.create_user(
            username="fx_plain", password="Password@12345", email="fx_plain@zic.tz"
        )
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
        self.partner = make_partner()

    def _make_commitment(self, number, currency="TZS", premium="250000.00"):
        return OLCommitment.objects.create(
            commitment_number=number,
            source_type="MANUAL",
            currency=currency,
            due_date=date(2026, 9, 1),
            premium_amount=premium,
            status="PENDING",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )

    def _create_and_post(self, amount="250000.00", currency="TZS", **overrides):
        payload = {
            "payer_name": "Jane Doe",
            "receipt_date": date(2026, 8, 25).isoformat(),
            "receipt_amount": amount,
            "currency": currency,
            "branch": str(self.branch.pk),
            "partner": str(self.partner.pk),
        }
        payload.update(overrides)
        created = self.client.post(f"{BASE}/", payload, format="json").data["data"]
        posted = self.client.post(f"{BASE}/{created['id']}/post/", {"reason": "Money confirmed."}, format="json")
        self.assertEqual(posted.status_code, 200, posted.data)
        return posted.data["data"]

    def _allocate(self, receipt_id, target_id, amount, **overrides):
        payload = {
            "target_type": "OL_COMMITMENT",
            "target_id": target_id,
            "amount": str(amount),
        }
        payload.update(overrides)
        return self.client.post(f"{BASE}/{receipt_id}/allocate/", payload, format="json")

    def test_same_currency_allocation_records_default_conversion(self):
        commitment = self._make_commitment("OLC-FX-SAME", premium="100000.00")
        receipt = self._create_and_post(amount="100000.00", currency="TZS")
        response = self._allocate(receipt["id"], commitment.commitment_number, "100000.00")

        self.assertEqual(response.status_code, 201, response.data)
        allocation = ReceiptAllocation.objects.get(receipt_id=receipt["id"])
        self.assertEqual(allocation.amount, Decimal("100000.00"))
        self.assertEqual(allocation.currency, "TZS")
        self.assertEqual(allocation.exchange_rate_used, Decimal("1.000000"))
        self.assertEqual(allocation.exchange_rate_source, "SAME_CURRENCY")
        self.assertEqual(allocation.converted_amount, Decimal("100000.00"))
        self.assertEqual(allocation.converted_currency, "TZS")

        alloc = response.data["data"]["allocations"][0]
        self.assertEqual(alloc["allocation_amount_in_receipt_currency"], "100000.00")
        self.assertEqual(alloc["allocation_amount_in_target_currency"], "100000.00")
        self.assertEqual(alloc["exchange_rate_used"], "1.000000")
        self.assertEqual(alloc["converted_amount"], "100000.00")

    def test_cross_currency_allocation_with_explicit_rate(self):
        commitment = self._make_commitment("OLC-FX-CROSS")
        receipt = self._create_and_post(amount="5000.00", currency="USD")
        response = self._allocate(receipt["id"], commitment.commitment_number, "5000.00", exchange_rate="50")

        self.assertEqual(response.status_code, 201, response.data)
        allocation = ReceiptAllocation.objects.get(receipt_id=receipt["id"])
        self.assertEqual(allocation.amount, Decimal("5000.00"))
        self.assertEqual(allocation.currency, "USD")
        self.assertEqual(allocation.exchange_rate, Decimal("50.00000000"))
        self.assertEqual(allocation.exchange_rate_used, Decimal("50.000000"))
        self.assertEqual(allocation.exchange_rate_source, "EXPLICIT")
        self.assertEqual(allocation.converted_amount, Decimal("250000.00"))
        self.assertEqual(allocation.converted_currency, "TZS")

        commitment.refresh_from_db()
        self.assertEqual(commitment.amount_paid, Decimal("250000.00"))
        self.assertEqual(commitment.balance, Decimal("0.00"))
        self.assertEqual(commitment.status, "COMPLETED")

        alloc = response.data["data"]["allocations"][0]
        self.assertEqual(alloc["allocation_amount_in_receipt_currency"], "5000.00")
        self.assertEqual(alloc["allocation_amount_in_target_currency"], "250000.00")

    def test_cross_currency_missing_rate_error(self):
        commitment = self._make_commitment("OLC-FX-MISS")
        receipt = self._create_and_post(amount="5000.00", currency="USD")
        response = self._allocate(receipt["id"], commitment.commitment_number, "5000.00")

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.data["error_code"], "RECEIPT_CURRENCY_MISMATCH")
        self.assertTrue(response.data["resolution_steps"])
        self.assertIn("exchange_rate", response.data["field_errors"])
        # Nothing must be written when the rate is missing.
        self.assertFalse(ReceiptAllocation.objects.filter(receipt_id=receipt["id"]).exists())
        commitment.refresh_from_db()
        self.assertEqual(commitment.amount_paid, Decimal("0.00"))

    def test_zero_and_negative_rate_blocked(self):
        commitment = self._make_commitment("OLC-FX-BAD")
        receipt = self._create_and_post(amount="5000.00", currency="USD")
        for rate in ("0", "-5"):
            response = self._allocate(receipt["id"], commitment.commitment_number, "5000.00", exchange_rate=rate)
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn("exchange_rate", response.data.get("field_errors", {}))
        self.assertFalse(ReceiptAllocation.objects.filter(receipt_id=receipt["id"]).exists())

    def test_converted_amount_math_and_partial_status(self):
        commitment = self._make_commitment("OLC-FX-MATH", premium="1000000.00")
        receipt = self._create_and_post(amount="2000.00", currency="USD")
        response = self._allocate(receipt["id"], commitment.commitment_number, "2000.00", exchange_rate="230.05")

        self.assertEqual(response.status_code, 201, response.data)
        allocation = ReceiptAllocation.objects.get(receipt_id=receipt["id"])
        self.assertEqual(allocation.converted_amount, Decimal("460100.00"))
        commitment.refresh_from_db()
        self.assertEqual(commitment.amount_paid, Decimal("460100.00"))
        self.assertEqual(commitment.balance, Decimal("539900.00"))
        self.assertEqual(commitment.status, "PARTIALLY_PAID")

    def test_exchange_rate_endpoint_returns_configured_rate(self):
        ExchangeRate.objects.create(
            from_currency="USD", to_currency="TZS", rate="2500.00",
            effective_date=date(2026, 8, 1), source="MANUAL",
        )
        response = self.client.get(f"{BASE}/exchange-rate/", {"from": "USD", "to": "TZS"})

        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["from_currency"], "USD")
        self.assertEqual(data["to_currency"], "TZS")
        self.assertEqual(Decimal(data["rate"]), Decimal("2500"))
        self.assertEqual(data["effective_date"], "2026-08-01")
        self.assertEqual(data["source"], "MANUAL")
        self.assertTrue(data["is_active"])
        self.assertFalse(data["stale"])

    def test_exchange_rate_endpoint_date_lookup_and_not_found(self):
        ExchangeRate.objects.create(
            from_currency="USD", to_currency="TZS", rate="2400",
            effective_date=date(2026, 6, 1), source="MANUAL",
        )
        ExchangeRate.objects.create(
            from_currency="USD", to_currency="TZS", rate="2500",
            effective_date=date(2026, 8, 1), source="MANUAL",
        )
        as_of = self.client.get(f"{BASE}/exchange-rate/", {"from": "USD", "to": "TZS", "date": "2026-07-15"})
        self.assertEqual(as_of.status_code, 200, as_of.data)
        self.assertEqual(Decimal(as_of.data["data"]["rate"]), Decimal("2400"))
        self.assertEqual(as_of.data["data"]["effective_date"], "2026-06-01")

        latest = self.client.get(f"{BASE}/exchange-rate/", {"from": "USD", "to": "TZS"})
        self.assertEqual(latest.status_code, 200, latest.data)
        self.assertEqual(Decimal(latest.data["data"]["rate"]), Decimal("2500"))

        missing = self.client.get(f"{BASE}/exchange-rate/", {"from": "EUR", "to": "TZS"})
        self.assertEqual(missing.status_code, 422)
        self.assertEqual(missing.data["error_code"], "RECEIPT_CURRENCY_MISMATCH")
        self.assertTrue(missing.data["resolution_steps"])

    def test_exchange_rate_endpoint_validates_codes_and_date(self):
        bad_codes = self.client.get(f"{BASE}/exchange-rate/", {"from": "US", "to": "TZ"})
        self.assertEqual(bad_codes.status_code, 422)
        self.assertEqual(bad_codes.data["error_code"], "RECEIPT_CURRENCY_MISMATCH")
        self.assertIn("from", bad_codes.data["field_errors"])

        bad_date = self.client.get(f"{BASE}/exchange-rate/", {"from": "USD", "to": "TZS", "date": "not-a-date"})
        self.assertEqual(bad_date.status_code, 422)
        self.assertIn("date", bad_date.data["field_errors"])

    def test_cross_currency_resolves_table_rate_with_stale_warning(self):
        group = ParameterGroup.objects.create(code="FX_TEST", name="FX Test")
        SystemParameter.objects.create(
            group=group, code="RECEIPT_EXCHANGE_RATE_STALE_DAYS", name="Exchange rate stale days",
            value_type="INTEGER", integer_value=30, is_active=True,
        )
        ExchangeRate.objects.create(
            from_currency="USD", to_currency="TZS", rate="50",
            effective_date=date.today() - timedelta(days=60), source="MANUAL",
        )
        commitment = self._make_commitment("OLC-FX-TABLE")
        receipt = self._create_and_post(amount="5000.00", currency="USD")
        response = self._allocate(receipt["id"], commitment.commitment_number, "5000.00")

        self.assertEqual(response.status_code, 201, response.data)
        self.assertIn("warning", response.data)
        allocation = ReceiptAllocation.objects.get(receipt_id=receipt["id"])
        self.assertEqual(allocation.converted_amount, Decimal("250000.00"))
        self.assertEqual(allocation.exchange_rate_source, "EXCHANGE_RATE_TABLE:MANUAL")

        lookup = self.client.get(f"{BASE}/exchange-rate/", {"from": "USD", "to": "TZS"})
        self.assertTrue(lookup.data["data"]["stale"])

    def test_audit_values_captured(self):
        commitment = self._make_commitment("OLC-FX-AUDIT")
        receipt = self._create_and_post(amount="5000.00", currency="USD")
        response = self._allocate(receipt["id"], commitment.commitment_number, "5000.00", exchange_rate="50")
        self.assertEqual(response.status_code, 201, response.data)

        allocation = ReceiptAllocation.objects.get(receipt_id=receipt["id"])
        audit = AuditLog.objects.filter(
            entity_type="receiptallocation", entity_id=allocation.pk, action_type="CREATE"
        ).first()
        self.assertIsNotNone(audit, "ReceiptAllocation must be audited on create")
        self.assertEqual(audit.after_state["exchange_rate_used"], "50.000000")
        self.assertEqual(audit.after_state["exchange_rate_source"], "EXPLICIT")
        self.assertEqual(audit.after_state["converted_amount"], "250000.00")
        self.assertEqual(audit.after_state["converted_currency"], "TZS")

    def test_auto_allocate_skips_cross_currency_commitments(self):
        same = self._make_commitment("OLC-FX-AUTO-SAME", premium="60000.00")
        self._make_commitment("OLC-FX-AUTO-CROSS", currency="USD", premium="500000.00")
        receipt = self._create_and_post(amount="100000.00", currency="TZS")
        response = self.client.post(f"{BASE}/{receipt['id']}/auto-allocate/", {}, format="json")

        self.assertEqual(response.status_code, 200, response.data)
        data = response.data["data"]
        self.assertEqual(data["commitments_count"], 1)
        self.assertEqual(data["allocations"][0]["commitment_number"], same.commitment_number)
        self.assertEqual(data["allocations"][0]["allocation_amount_in_target_currency"], "60000.00")

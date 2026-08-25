import csv
import io
from datetime import date

from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APITestCase

from apps.front_office.receipts.models import Receipt, ReceiptStatus
from apps.front_office.receipts.services.work_queue import LIST_COLUMNS
from apps.ol_commitments.models import OLCommitment
from apps.ol_parameters.models import OLCommitmentStatus
from apps.partner_onboarding.models import Branch
from apps.partners.models import Partner
from apps.users.models import UserGroup

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
        "partner_number": f"WQ{seq:04d}",
        "partner_type": "INDIVIDUAL",
        "party_type": "INDIVIDUAL",
        "first_name": "Jane",
        "surname": "Doe",
        "email": f"wq{seq}@zic.tz",
        "mobile_number": f"2557000000{seq}",
        "is_active": True,
        "status": "ACTIVE",
    }
    defaults.update(overrides)
    return Partner.objects.create(**defaults)


class ReceiptWorkQueueApiTests(APITestCase):
    def setUp(self):
        call_command("seed_receipt_parameters")
        call_command("seed_receipt_permissions")
        seed_commitment_statuses()
        self.admin = User.objects.create_superuser(
            username="wq_admin", password="Password@12345", email="wq_admin@zic.tz"
        )
        self.viewer = User.objects.create_user(
            username="wq_viewer", password="Password@12345", email="wq_viewer@zic.tz"
        )
        UserGroup.objects.get(code="RECEIPT_VIEWER").users.add(self.viewer)
        self.client.force_authenticate(self.admin)
        self.branch = Branch.objects.create(code="DAR", name="Dar es Salaam")
        self.partner = make_partner()
        self.commitment = OLCommitment.objects.create(
            commitment_number="OLC-WQ-0001",
            source_type="MANUAL",
            currency="TZS",
            due_date=date(2026, 9, 1),
            premium_amount="100000.00",
            status="PENDING",
            partner=self.partner,
            partner_name_snapshot=str(self.partner),
            source_channel="API",
        )

    def _create_draft(self, payer_name="Jane Doe", receipt_date=date(2026, 8, 20), amount="100000.00", **overrides):
        payload = {
            "payer_name": payer_name,
            "receipt_date": receipt_date.isoformat(),
            "receipt_amount": amount,
            "currency": "TZS",
            "payment_mode": "CASH",
            "branch": str(self.branch.pk),
            "partner": str(self.partner.pk),
        }
        payload.update(overrides)
        return self.client.post(f"{BASE}/", payload, format="json").data["data"]

    def _create_and_post(self, payer_name="Jane Doe", receipt_date=date(2026, 8, 20), amount="100000.00", **overrides):
        created = self._create_draft(payer_name=payer_name, receipt_date=receipt_date, amount=amount, **overrides)
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

    def _reverse(self, receipt_id, reason="Collected in error."):
        return self.client.post(f"{BASE}/{receipt_id}/reverse/", {"reason": reason}, format="json")

    # --- list columns and display names -------------------------------------

    def test_list_columns_and_display_names(self):
        created = self._create_and_post()
        self._allocate(created["id"], self.commitment.commitment_number, "100000.00")

        response = self.client.get(f"{BASE}/")
        self.assertEqual(response.status_code, 200)
        row = response.data["data"]["results"][0]
        for column in LIST_COLUMNS:
            self.assertIn(column, row, f"missing list column {column}")
        self.assertEqual(row["payer_display"], "Jane Doe")
        self.assertEqual(row["branch_display"], "Dar es Salaam")
        self.assertEqual(row["payment_mode_display"], "Cash")
        self.assertEqual(row["currency_display"], "TZS")
        self.assertEqual(row["status"], ReceiptStatus.FULLY_ALLOCATED)
        self.assertEqual(row["status_display"], "Fully allocated")
        self.assertEqual(row["source_module"], "MANUAL")
        self.assertEqual(row["source_module_display"], "Manual")
        self.assertEqual(row["created_by_display"], "wq_admin")
        self.assertEqual(row["posted_by_display"], "wq_admin")
        self.assertIsNotNone(row["receipt_number"])
        self.assertTrue(row["receipt_number"].startswith("RCT-"))
        # Names are surfaced, never UUIDs.
        self.assertNotEqual(row["payer_display"], str(created["id"]))
        self.assertNotEqual(row["branch_display"], str(self.branch.pk))

    # --- filters -------------------------------------------------------------

    def test_list_filters(self):
        a = self._create_and_post()  # DAR / TZS / CASH / MANUAL, posted
        self.assertEqual(a["status"], ReceiptStatus.POSTED)
        b = self._create_and_post(
            payer_name="Alice Smith",
            amount="50000.00",
            payment_mode="CHEQUE",
            payment_reference="CHQ-2026-001",
            source_module="OL_POLICY",
            source_reference_type="POLICY_NUMBER",
            source_reference_id="POL-2026-1",
        )
        self.assertEqual(b["status"], ReceiptStatus.POSTED)

        other_branch = Branch.objects.create(code="ARU", name="Arusha")
        c = self._create_and_post(branch=str(other_branch.pk), amount="20000.00")
        self.assertEqual(c["status"], ReceiptStatus.POSTED)
        self._reverse(c["id"])

        draft = self._create_draft(payer_name="Draft Payer", amount="30000.00")

        cases = {
            "status": ("status", "POSTED", {a["id"], b["id"]}),
            "branch": ("branch", str(self.branch.pk), {a["id"], b["id"], draft["id"]}),
            "currency": ("currency", "TZS", {a["id"], b["id"], c["id"], draft["id"]}),
            "payment_mode": ("payment_mode", "CHEQUE", {b["id"]}),
            "payer": ("payer", "Alice", {b["id"]}),
            "source_module": ("source_module", "OL_POLICY", {b["id"]}),
        }
        for label, (param, value, expected) in cases.items():
            resp = self.client.get(f"{BASE}/", {param: value})
            self.assertEqual(resp.status_code, 200)
            got = {row["id"] for row in resp.data["data"]["results"]}
            self.assertEqual(got, expected, f"{label} filter mismatch")

        date_resp = self.client.get(
            f"{BASE}/", {"receipt_date_from": "2026-08-20", "receipt_date_to": "2026-08-20"}
        )
        self.assertEqual(
            {row["id"] for row in date_resp.data["data"]["results"]},
            {a["id"], b["id"], c["id"], draft["id"]},
        )

        unallocated = self.client.get(f"{BASE}/", {"unallocated_only": "true"})
        self.assertEqual(
            {row["id"] for row in unallocated.data["data"]["results"]},
            {a["id"], b["id"], c["id"], draft["id"]},
        )

        reversed_resp = self.client.get(f"{BASE}/", {"reversed_only": "true"})
        self.assertEqual({row["id"] for row in reversed_resp.data["data"]["results"]}, {c["id"]})
        self.assertEqual(reversed_resp.data["data"]["results"][0]["status"], ReceiptStatus.REVERSED)

    # --- search --------------------------------------------------------------

    def test_list_search(self):
        a = self._create_and_post()  # Jane Doe, CASH, RCT-...
        b = self._create_and_post(
            payer_name="Alice Smith",
            amount="50000.00",
            payment_mode="CHEQUE",
            payment_reference="CHQ-2026-001",
            source_module="OL_POLICY",
            source_reference_type="POLICY_NUMBER",
            source_reference_id="POL-2026-1",
        )

        for term, expected in (
            (a["receipt_number"], {a["id"]}),
            (a["receipt_number"][:6], {a["id"], b["id"]}),
            ("Jane Doe", {a["id"], b["id"]}),  # a via payer name, b via shared partner snapshot
            ("Alice", {b["id"]}),
            ("CHQ-2026-001", {b["id"]}),
            ("POL-2026-1", {b["id"]}),
        ):
            resp = self.client.get(f"{BASE}/", {"search": term})
            self.assertEqual(resp.status_code, 200)
            self.assertEqual(
                {row["id"] for row in resp.data["data"]["results"]},
                expected,
                f"search term {term!r} mismatch",
            )

    # --- KPI math ------------------------------------------------------------

    def test_kpis_math(self):
        a = self._create_and_post(amount="100000.00", receipt_date=date(2026, 8, 20))
        self._allocate(a["id"], self.commitment.commitment_number, "100000.00")
        _b = self._create_and_post(amount="50000.00", receipt_date=date(2026, 8, 21))
        c = self._create_and_post(amount="25000.00", receipt_date=date(2026, 8, 22))
        self._reverse(c["id"])

        response = self.client.get(f"{BASE}/kpis/")
        self.assertEqual(response.status_code, 200)
        data = response.data["data"]
        self.assertEqual(data["total_received_period"], "175000.00")
        self.assertEqual(data["total_allocated_period"], "100000.00")
        self.assertEqual(data["total_unallocated"], "50000.00")
        self.assertEqual(data["receipt_count"], 3)
        self.assertEqual(data["reversed_amount"], "25000.00")

        period = self.client.get(
            f"{BASE}/kpis/", {"receipt_date_from": "2026-08-21", "receipt_date_to": "2026-08-22"}
        )
        pd = period.data["data"]
        self.assertEqual(pd["total_received_period"], "75000.00")
        self.assertEqual(pd["total_allocated_period"], "0.00")
        self.assertEqual(pd["total_unallocated"], "50000.00")
        self.assertEqual(pd["receipt_count"], 2)
        self.assertEqual(pd["reversed_amount"], "25000.00")
        self.assertEqual(pd["period"]["receipt_date_from"], "2026-08-21")
        self.assertEqual(pd["period"]["receipt_date_to"], "2026-08-22")

        reversed_only = self.client.get(f"{BASE}/kpis/", {"reversed_only": "true"})
        rd = reversed_only.data["data"]
        self.assertEqual(rd["total_received_period"], "25000.00")
        self.assertEqual(rd["total_allocated_period"], "0.00")
        self.assertEqual(rd["total_unallocated"], "0.00")
        self.assertEqual(rd["receipt_count"], 1)
        self.assertEqual(rd["reversed_amount"], "25000.00")

    # --- allowed actions by status and permission ----------------------------

    def test_allowed_actions_by_status(self):
        draft = self._create_draft()
        self.assertEqual(draft["allowed_actions"], ["update", "post", "cancel"])

        posted = self._create_and_post()
        self.assertEqual(posted["allowed_actions"], ["allocate", "reverse"])

        allocated = self._create_and_post(amount="100000.00")
        self._allocate(allocated["id"], self.commitment.commitment_number, "100000.00")
        full = self.client.get(f"{BASE}/{allocated['id']}/").data["data"]
        self.assertEqual(full["allowed_actions"], ["reverse"])

        reversed_resp = self.client.get(f"{BASE}/{posted['id']}/")
        reversed_receipt = reversed_resp.data["data"]
        reversed_data = self.client.post(
            f"{BASE}/{posted['id']}/reverse/", {"reason": "Collected in error."}, format="json"
        ).data["data"]
        self.assertEqual(reversed_data["status"], ReceiptStatus.REVERSED)
        self.assertEqual(reversed_data["allowed_actions"], [])
        self.assertEqual(reversed_receipt["allowed_actions"], ["allocate", "reverse"])

    def test_allowed_actions_permission_aware(self):
        self._create_draft()
        self.client.force_authenticate(self.viewer)

        list_response = self.client.get(f"{BASE}/")
        self.assertEqual(list_response.status_code, 200)
        row = list_response.data["data"]["results"][0]
        self.assertEqual(row["allowed_actions"], [])

        detail = self.client.get(f"{BASE}/{row['id']}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.data["data"]["allowed_actions"], [])

    # --- CSV export ----------------------------------------------------------

    def test_csv_export_respects_filters(self):
        a = self._create_and_post(amount="100000.00")
        self._allocate(a["id"], self.commitment.commitment_number, "100000.00")
        _b = self._create_and_post(amount="50000.00", payment_mode="CHEQUE", payment_reference="CHQ-2026-001")
        c = self._create_and_post(amount="25000.00")
        self._reverse(c["id"])

        response = self.client.get(f"{BASE}/export/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertTrue(response["Content-Disposition"].startswith("attachment; filename="))
        rows = list(csv.reader(io.StringIO(response.content.decode("utf-8"))))
        self.assertEqual(rows[0], list(LIST_COLUMNS))
        self.assertEqual(len(rows), 4)  # header + three receipts

        filtered = self.client.get(f"{BASE}/export/", {"status": ReceiptStatus.REVERSED})
        rows = list(csv.reader(io.StringIO(filtered.content.decode("utf-8"))))
        self.assertEqual(len(rows), 2)  # header + one reversed receipt
        self.assertEqual(rows[1][9], ReceiptStatus.REVERSED)  # status column index

        filtered = self.client.get(f"{BASE}/export/", {"currency": "TZS", "status": ReceiptStatus.POSTED})
        rows = list(csv.reader(io.StringIO(filtered.content.decode("utf-8"))))
        self.assertEqual(len(rows), 2)  # header + one posted receipt (b)
        self.assertEqual(rows[1][6], "50000.00")  # receipt_amount column index

    # --- detail: allocations, reversal, audit timeline ------------------------

    def test_detail_includes_allocations_reversal_audit_timeline(self):
        created = self._create_and_post(amount="100000.00")
        self._allocate(created["id"], self.commitment.commitment_number, "100000.00")
        self._reverse(created["id"], reason="Client requested refund.")

        detail = self.client.get(f"{BASE}/{created['id']}/")
        self.assertEqual(detail.status_code, 200)
        data = detail.data["data"]

        # Receipt header.
        self.assertEqual(data["status"], ReceiptStatus.REVERSED)
        self.assertEqual(data["payer_display"], "Jane Doe")

        # Allocations include the original (marked REVERSED) and the reversal row.
        self.assertGreaterEqual(len(data["allocations"]), 2)
        statuses = {alloc["allocation_status"] for alloc in data["allocations"]}
        self.assertIn("REVERSED", statuses)
        self.assertTrue(any(alloc.get("reversal_of") for alloc in data["allocations"]))

        # Reversal history.
        self.assertEqual(len(data["reversals"]), 1)
        reversal = data["reversals"][0]
        self.assertTrue(reversal["reversal_number"].startswith("RVR-"))
        self.assertEqual(reversal["reason"], "Client requested refund.")
        self.assertEqual(reversal["reversed_by_name"], "wq_admin")
        self.assertIsInstance(reversal["reversed_allocations"], list)

        # Documents (list container present).
        self.assertIsInstance(data["documents"], list)

        # Status history includes the posted transition.
        transitions = {h["from_status"]: h["to_status"] for h in data["status_history"]}
        self.assertEqual(transitions.get("DRAFT"), ReceiptStatus.POSTED)
        self.assertIn(ReceiptStatus.REVERSED, transitions.values())

        # Audit timeline is the central, ordered, actor-bearing trail.
        timeline = data["audit_timeline"]
        self.assertIsInstance(timeline, list)
        self.assertGreater(len(timeline), 0)
        entities = {entry["entity"] for entry in timeline}
        self.assertIn("receipt", entities)
        self.assertIn("receiptallocation", entities)
        self.assertIn("receiptreversal", entities)
        create_entry = next(e for e in timeline if e["entity"] == "receipt" and e["action"] == "CREATE")
        self.assertEqual(create_entry["actor"], "wq_admin")
        for entry in timeline:
            self.assertIn("action", entry)
            self.assertIn("timestamp", entry)
            self.assertIn("changed_fields", entry)
            self.assertIn("reason", entry)

    # --- audit timeline via the DB (defensive read-side check) ----------------

    def test_audit_timeline_query_covers_related_records(self):
        created = self._create_and_post(amount="100000.00")
        self._allocate(created["id"], self.commitment.commitment_number, "100000.00")
        self._reverse(created["id"])

        receipt = Receipt.objects.get(pk=created["id"])
        from apps.front_office.receipts.services.work_queue import audit_timeline

        timeline = audit_timeline(receipt)
        entities = {entry["entity"] for entry in timeline}
        self.assertIn("receipt", entities)
        self.assertIn("receiptallocation", entities)
        self.assertIn("receiptreversal", entities)
        self.assertIn("receiptstatushistory", entities)

from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework import status
from .models import FOReceipt, FOCommission, FORequisition
from apps.users.models import User

class FrontOfficeTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="front-office-test",
            email="front-office-test@example.com",
            password="TestPass123!",
        )
        self.client.force_authenticate(user=self.user)
        self.receipt = FOReceipt.objects.create(
            receipt_number="REC-001",
            amount=100.00,
            payment_method="CASH",
            payment_date="2023-10-01",
            reference="POL-123"
        )
        self.commission = FOCommission.objects.create(
            agent_id="AGT-001",
            policy_reference="POL-123",
            amount=50.00
        )
        self.requisition = FORequisition.objects.create(
            requisition_number="REQ-001",
            department="IT",
            amount=500.00,
            reason="New laptops"
        )

    def test_list_receipts(self):
        response = self.client.get("/api/v1/front-office/legacy/receipts/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Checking actual length since this tests the model setup properly
        # Django Rest Framework usually paginates, check results or directly if no pagination
        data = response.json()
        if "results" in data:
            self.assertEqual(len(data["results"]), 1)
        elif "data" in data:
            self.assertEqual(len(data["data"]), 1)
        else:
            self.assertEqual(len(data), 1)

    def test_create_commission(self):
        payload = {
            "agent_id": "AGT-002",
            "policy_reference": "POL-456",
            "amount": "75.00"
        }
        response = self.client.post("/api/v1/front-office/commissions/", payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(FOCommission.objects.count(), 2)

    def test_update_requisition(self):
        payload = {
            "requisition_number": "REQ-001",
            "department": "IT",
            "amount": "500.00",
            "reason": "New laptops",
            "status": "APPROVED"
        }
        response = self.client.patch(f"/api/v1/front-office/requisitions/{self.requisition.id}/", payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.requisition.refresh_from_db()
        self.assertEqual(self.requisition.status, "APPROVED")

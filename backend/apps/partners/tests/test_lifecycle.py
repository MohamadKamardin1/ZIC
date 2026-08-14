import uuid

import pytest
from django.urls import reverse
from rest_framework.test import APIClient

from apps.partner_onboarding.models import Branch, Location
from apps.partners.models import (
    Partner,
    PartnerDocument,
    PartnerType,
    PartnerTypeAssignment,
    PartnerTypeDocumentRequirement,
)
from apps.users.models import User


def make_user(**overrides):
    values = {
        "email": f"user-{uuid.uuid4().hex[:8]}@example.com",
        "username": f"user-{uuid.uuid4().hex[:8]}",
        "password": "TestPassword123!",
        "first_name": "Test",
        "last_name": "User",
    }
    values.update(overrides)
    return User.objects.create_user(**values)


def make_partner(**overrides):
    values = {
        "partner_number": f"PN-{uuid.uuid4().hex[:10].upper()}",
        "partner_type": "INDIVIDUAL",
        "partner_category": "INDIVIDUAL",
        "first_name": "Asha",
        "surname": "Ali",
        "email": f"partner-{uuid.uuid4().hex[:8]}@example.com",
        "mobile_number": f"+2557{uuid.uuid4().int % 10**8:08d}",
        "status": "ACTIVE",
    }
    values.update(overrides)
    return Partner.objects.create(**values)


def make_assignment(partner=None, partner_type=None):
    partner = partner or make_partner()
    partner_type = partner_type or PartnerType.objects.create(
        code=f"TYPE-{uuid.uuid4().hex[:8].upper()}",
        name="Broker",
    )
    return PartnerTypeAssignment.objects.create(partner=partner, partner_type=partner_type)


def make_admin_client():
    client = APIClient()
    client.force_authenticate(user=make_user(is_superuser=True, is_staff=True))
    return client


@pytest.mark.django_db
class TestPartnerAssignmentHardening:
    def test_assignment_rejects_multiple_branches_instead_of_discarding_data(self):
        partner = make_partner()
        partner_type = PartnerType.objects.create(
            code=f"TYPE-{uuid.uuid4().hex[:8].upper()}", name="Agent"
        )
        branch_a = Branch.objects.create(code=f"B-{uuid.uuid4().hex[:6].upper()}", name="North")
        branch_b = Branch.objects.create(code=f"B-{uuid.uuid4().hex[:6].upper()}", name="South")

        client = make_admin_client()
        response = client.post(
            reverse("v1:partners-assign-partner-type", args=[partner.id]),
            {
                "partner_type": str(partner_type.id),
                "branches": [str(branch_a.id), str(branch_b.id)],
            },
            format="json",
        )

        assert response.status_code == 400
        error_message = response.data["error"]["message"]
        assert "branches" in error_message
        assert not PartnerTypeAssignment.objects.filter(partner=partner).exists()

    def test_assignment_generates_setup_records_and_history(self):
        partner = make_partner()
        partner_type = PartnerType.objects.create(
            code=f"TYPE-{uuid.uuid4().hex[:8].upper()}", name="Broker"
        )
        PartnerTypeDocumentRequirement.objects.create(
            partner_type=partner_type,
            code="LICENSE",
            description="Operating license",
            is_required=True,
        )
        branch = Branch.objects.create(code=f"B-{uuid.uuid4().hex[:6].upper()}", name="Central")
        location = Location.objects.create(
            branch=branch,
            code=f"L-{uuid.uuid4().hex[:6].upper()}",
            name="Stone Town",
        )

        client = make_admin_client()
        response = client.post(
            reverse("v1:partners-assign-partner-type", args=[partner.id]),
            {
                "partner_type": str(partner_type.id),
                "branch": str(branch.id),
                "location": str(location.id),
            },
            format="json",
        )

        assert response.status_code == 201
        assignment = PartnerTypeAssignment.objects.get(partner=partner, partner_type=partner_type)
        assert PartnerDocument.objects.filter(assignment=assignment, document_requirement__code="LICENSE").exists()
        history_response = client.get(reverse("v1:assignment-history", args=[assignment.id]))
        assert history_response.status_code == 200
        assert history_response.data["data"][0]["new_status"] == "ACTIVE"

    def test_assignment_lifecycle_is_auditable_and_admin_only(self):
        assignment = make_assignment()
        client = make_admin_client()

        deactivate = client.post(
            reverse("v1:assignment-deactivate", args=[assignment.id]),
            {"reason": "Contract expired"},
            format="json",
        )
        assert deactivate.status_code == 200
        assignment.refresh_from_db()
        assert assignment.status == "INACTIVE"
        assert assignment.status_history.count() == 1
        assert assignment.status_history.first().reason == "Contract expired"

        activate = client.post(reverse("v1:assignment-activate", args=[assignment.id]), format="json")
        assert activate.status_code == 200
        assignment.refresh_from_db()
        assert assignment.status == "ACTIVE"
        assert assignment.status_history.count() == 2

        non_admin = APIClient()
        non_admin.force_authenticate(user=make_user())
        denied = non_admin.post(reverse("v1:assignment-deactivate", args=[assignment.id]), format="json")
        assert denied.status_code == 403

    def test_assignment_nested_document_is_scoped_to_parent_assignment(self):
        first = make_assignment()
        second = make_assignment()
        document = PartnerDocument.objects.create(assignment=second, status="NOT_SUBMITTED")
        client = make_admin_client()

        response = client.patch(
            reverse(
                "v1:assignment-setup-document-detail",
                args=[first.id, document.id],
            ),
            {"status": "UNDER_REVIEW"},
            format="json",
        )

        assert response.status_code == 404
        document.refresh_from_db()
        assert document.status == "NOT_SUBMITTED"

    def test_non_admin_cannot_mutate_partner_type_configuration(self):
        partner_type = PartnerType.objects.create(
            code=f"TYPE-{uuid.uuid4().hex[:8].upper()}", name="Agent"
        )
        client = APIClient()
        client.force_authenticate(user=make_user())

        response = client.post(
            reverse("v1:partner-type-documents", args=[partner_type.id]),
            {"code": "LICENSE", "description": "License", "is_required": True},
            format="json",
        )

        assert response.status_code == 403

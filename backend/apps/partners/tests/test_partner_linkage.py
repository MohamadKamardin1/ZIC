import uuid
from datetime import timedelta

import pytest
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from apps.common.models import DomainEvent
from apps.partners.models import Partner, UserPartnerLink
from apps.users.models import User, UserActivityLog


def make_user(**overrides):
    values = {
        "email": f"user-{uuid.uuid4().hex[:8]}@example.com",
        "username": f"user-{uuid.uuid4().hex[:8]}",
        "password": "TestPassword123!",
        "first_name": "Partner",
        "last_name": "User",
        "user_type": "PARTNER",
        "status": "ACTIVE",
    }
    values.update(overrides)
    return User.objects.create_user(**values)


def make_partner(**overrides):
    values = {
        "partner_number": f"PN-{uuid.uuid4().hex[:10].upper()}",
        "partner_type": "INDIVIDUAL",
        "partner_category": "INDIVIDUAL",
        "party_type": "INDIVIDUAL",
        "first_name": "Asha",
        "surname": "Ali",
        "email": f"partner-{uuid.uuid4().hex[:8]}@example.com",
        "mobile_number": f"+2557{uuid.uuid4().int % 10**8:08d}",
        "status": "ACTIVE",
        "is_active": True,
    }
    values.update(overrides)
    return Partner.objects.create(**values)


def admin_client():
    client = APIClient()
    client.force_authenticate(user=make_user(is_superuser=True, is_staff=True, user_type="SUPER_ADMIN"))
    return client


@pytest.mark.django_db
class TestPartnerLinkage:
    def test_partner_user_sees_only_active_currently_linked_partner(self):
        user = make_user()
        visible = make_partner()
        other = make_partner()
        UserPartnerLink.objects.create(user=user, partner=visible, is_primary=True)
        UserPartnerLink.objects.create(user=user, partner=other, link_status="INACTIVE")

        assert list(user.visible_partners()) == [visible]
        assert user.can_access_partner(visible)
        assert not user.can_access_partner(other)

    def test_expired_link_and_inactive_partner_are_not_visible(self):
        user = make_user()
        expired = make_partner()
        inactive = make_partner(status="INACTIVE")
        UserPartnerLink.objects.create(
            user=user,
            partner=expired,
            valid_to=timezone.now() - timedelta(minutes=1),
        )
        UserPartnerLink.objects.create(user=user, partner=inactive)

        assert not user.visible_partners().exists()
        assert not user.can_access_partner(expired)
        assert not user.can_access_partner(inactive)

    def test_internal_staff_bypasses_partner_scope_but_partner_user_does_not(self):
        first = make_partner()
        second = make_partner()
        partner_user = make_user()
        staff_user = make_user(user_type="STAFF", is_staff=True)
        UserPartnerLink.objects.create(user=partner_user, partner=first)

        assert set(partner_user.visible_partners()) == {first}
        assert set(staff_user.visible_partners()) == {first, second}

    def test_admin_can_create_set_primary_and_deactivate_link_with_audit(self):
        actor = make_user(is_superuser=True, is_staff=True, user_type="SUPER_ADMIN")
        user = make_user()
        partner = make_partner()
        client = APIClient()
        client.force_authenticate(user=actor)

        response = client.post(
            reverse("v1:partner-links-list"),
            {
                "user_id": str(user.id),
                "partner_id": str(partner.id),
                "is_primary": True,
            },
            format="json",
        )
        assert response.status_code == 201
        link = UserPartnerLink.objects.get(user=user, partner=partner)
        assert link.is_primary is True
        assert DomainEvent.objects.filter(event_type="iam.user.partner_linked").exists()

        deactivate = client.post(
            reverse("v1:partner-links-deactivate", args=[link.id]),
            {"reason": "Access removed"},
            format="json",
        )
        assert deactivate.status_code == 200
        link.refresh_from_db()
        assert link.link_status == "INACTIVE"
        assert not user.visible_partners().exists()
        assert UserActivityLog.objects.filter(
            user=user,
            details__event_type="iam.user.partner_unlinked",
        ).exists()

    def test_partner_context_endpoint_is_scoped(self):
        user = make_user()
        visible = make_partner()
        hidden = make_partner()
        UserPartnerLink.objects.create(user=user, partner=visible, is_primary=True)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("v1:partner-context"))
        assert response.status_code == 200
        payload = response.data["data"]
        assert payload["current_partner"]["id"] == str(visible.id)
        assert payload["partner_ids"] == [str(visible.id)]
        assert str(hidden.id) not in payload["partner_ids"]

    def test_partner_list_endpoint_is_scoped(self):
        user = make_user()
        visible = make_partner()
        hidden = make_partner()
        UserPartnerLink.objects.create(user=user, partner=visible)
        client = APIClient()
        client.force_authenticate(user=user)

        response = client.get(reverse("v1:partners-list"))
        assert response.status_code == 200
        results = response.data["data"]
        ids = {item["id"] for item in results}
        assert ids == {str(visible.id)}
        assert str(hidden.id) not in ids

    def test_non_admin_cannot_mutate_partner_links(self):
        user = make_user()
        client = APIClient()
        client.force_authenticate(user=user)
        response = client.post(
            reverse("v1:partner-links-list"),
            {"user_id": str(user.id), "partner_id": str(make_partner().id)},
            format="json",
        )
        assert response.status_code == 403

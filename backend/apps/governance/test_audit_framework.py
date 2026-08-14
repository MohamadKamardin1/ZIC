import uuid

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.governance.models import AuditLog
from apps.governance.services.audit_service import AuditContext, AuditService
from apps.partners.models import Partner, UserPartnerLink
from apps.users.models import User, UserGroup, UserPermission

pytestmark = pytest.mark.django_db


def make_user(username, *, is_staff=False, is_superuser=False):
    return User.objects.create_user(
        username=username,
        email=f"{username}@example.test",
        password="Test123!",
        first_name=username.title(),
        is_staff=is_staff,
        is_superuser=is_superuser,
    )


def make_partner(number):
    return Partner.objects.create(
        partner_number=number,
        partner_type="INDIVIDUAL",
        first_name="Audit",
        surname="Partner",
        email=f"{number.lower()}@example.test",
        mobile_number="+255711000000",
        status="ACTIVE",
        is_active=True,
    )


def test_user_creation_and_update_are_audited_with_state_diff():
    user = make_user("audit-user")
    created = AuditLog.objects.filter(
        app_label="users", model_name="user", object_id=str(user.pk), action="CREATE"
    ).latest("created_at")
    assert created.after_state["username"] == "audit-user"

    request = type(
        "Request",
        (),
        {
            "user": user,
            "path": "/api/v1/users/",
            "META": {},
            "request_id": "audit-update-test",
        },
    )()
    AuditContext.set_request(request)
    try:
        user.first_name = "Changed"
        user.save(update_fields=["first_name"])
    finally:
        AuditContext.clear()

    updated = AuditLog.objects.filter(
        app_label="users", model_name="user", object_id=str(user.pk), action="UPDATE"
    ).latest("created_at")
    assert updated.before_state["first_name"] == "Audit-User"
    assert updated.after_state["first_name"] == "Changed"
    assert "first_name" in updated.changed_fields
    assert updated.user == user


def test_group_permission_assignment_is_audited():
    user = make_user("group-audit")
    group = UserGroup.objects.create(name="Audit Group", code="AUDIT_GROUP")
    permission = UserPermission.objects.create(
        name="Read Audit",
        codename="audit.read",
        module="audit",
        action="READ",
    )

    group.permissions.add(permission)
    user.groups.add(group)

    permission_event = AuditLog.objects.filter(
        app_label="users", model_name="usergroup", action="ASSIGN", object_id=str(group.pk)
    ).latest("created_at")
    user_event = AuditLog.objects.filter(
        app_label="users", model_name="user", action="ASSIGN", object_id=str(user.pk)
    ).latest("created_at")
    assert permission_event.changed_fields == ["permissions"]
    assert user_event.changed_fields == ["groups"]


def test_partner_link_creation_is_audited():
    user = make_user("partner-audit")
    partner = make_partner("AUD-0001")
    link = UserPartnerLink.objects.create(user=user, partner=partner, is_primary=True)

    event = AuditLog.objects.filter(
        app_label="partners", model_name="userpartnerlink", object_id=str(link.pk)
    ).latest("created_at")
    assert event.action == "CREATE"
    assert event.after_state["user"] == str(user.pk)
    assert event.after_state["partner"] == str(partner.pk)


def test_audit_context_captures_correlation_and_request_metadata():
    user = make_user("context-audit")
    request = type(
        "Request",
        (),
        {
            "user": user,
            "path": "/api/v1/users/",
            "META": {
                "HTTP_X_REQUEST_ID": "corr-test-123",
                "HTTP_USER_AGENT": "audit-test-agent",
                "REMOTE_ADDR": "127.0.0.10",
            },
            "request_id": "corr-test-123",
        },
    )()
    AuditContext.set_request(request)
    try:
        event = AuditService.log_action("VERIFY", user, reason="correlation test")
    finally:
        AuditContext.clear()

    assert event.correlation_id == "corr-test-123"
    assert event.request_id == "corr-test-123"
    assert event.ip_address == "127.0.0.10"
    assert event.user_agent == "audit-test-agent"
    assert event.source_channel == AuditLog.SourceChannel.API


def test_audit_api_is_read_only_and_admin_only():
    admin = make_user("audit-admin", is_staff=True, is_superuser=True)
    regular = make_user("audit-regular")
    event = AuditService.log_action("VERIFY", regular, reason="api test")

    client = APIClient()
    client.force_authenticate(user=regular)
    response = client.get("/api/v1/governance/audit-logs/")
    assert response.status_code == 403

    client.force_authenticate(user=admin)
    response = client.get("/api/v1/governance/audit-logs/", {"model_name": "user", "action": "VERIFY"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert any(row["id"] == str(event.pk) for row in payload["data"])

    response = client.get(f"/api/v1/governance/audit-logs/{event.pk}/")
    assert response.status_code == 200


def test_audit_events_are_immutable():
    event = AuditService.log(
        action_type="CREATE",
        entity_type="Test",
        entity_id=uuid.uuid4(),
        entity_repr="immutable",
    )
    event.reason = "tampered"
    with pytest.raises(ValidationError):
        event.save()
    with pytest.raises(ValidationError):
        event.delete()

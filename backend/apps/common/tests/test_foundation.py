import uuid

import pytest

from apps.common.models import DomainEvent

pytestmark = pytest.mark.django_db


def test_domain_event_has_uuid_and_transitions_to_published():
    event = DomainEvent.objects.create(
        event_type="partner.created",
        aggregate_type="Partner",
        aggregate_id="partner-1",
        payload={"partnerNumber": "PN-001"},
    )

    assert isinstance(event.id, uuid.UUID)
    assert event.status == DomainEvent.Status.PENDING

    event.mark_published()
    event.refresh_from_db()

    assert event.status == DomainEvent.Status.PUBLISHED
    assert event.published_at is not None
    assert event.last_error == ""


def test_domain_event_records_failed_attempts():
    event = DomainEvent.objects.create(
        event_type="partner.updated",
        aggregate_type="Partner",
        aggregate_id="partner-2",
    )

    event.mark_failed(RuntimeError("broker unavailable"))
    event.refresh_from_db()

    assert event.status == DomainEvent.Status.FAILED
    assert event.attempts == 1
    assert event.last_error == "broker unavailable"

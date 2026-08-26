from datetime import date

import pytest
from apps.ol_parameters.management.commands.seed_zanzibar_ol_complete import Command
from apps.ol_parameters.models import (
    OLHealthQuestionnaireItem,
    OLInvestmentFund,
    OLMortalityRateRow,
    OLMortalityRateTable,
    OLPremiumRateRow,
    OLPremiumRateTable,
    OLRiderRateRow,
    OLRiderRateTable,
    OLRiderSetup,
)
from apps.users.models import User
from django.core.management import call_command
from django.db.models import Q
from rest_framework.test import APIClient

OPTION_ENTITIES = (
    "identity-types",
    "locations",
    "agents",
    "products",
    "plan-types",
    "payment-frequencies",
    "quote-bases",
    "premium-factors",
    "member-relations",
    "cover-types",
    "payment-modes",
    "investment-funds",
    "investment-fund-types",
    "riders",
    "benefit-types",
    "currencies",
)


def active_effective_queryset(model):
    queryset = model.objects.filter(is_active=True)
    field_names = {field.name for field in model._meta.fields}
    today = date.today()
    if "effective_from" in field_names:
        queryset = queryset.filter(
            Q(effective_from__isnull=True) | Q(effective_from__lte=today),
            Q(effective_to__isnull=True) | Q(effective_to__gte=today),
        )
    return queryset


@pytest.mark.django_db
def test_complete_seed_is_idempotent_and_covers_every_parameter_model():
    call_command("seed_zanzibar_ol_complete", verbosity=0)
    first_counts = {
        model._meta.label: active_effective_queryset(model).count()
        for model in Command.REQUIRED_MODELS
    }

    assert all(count > 0 for count in first_counts.values()), {
        label: count for label, count in first_counts.items() if count == 0
    }

    call_command("seed_zanzibar_ol_complete", verbosity=0)
    second_counts = {
        model._meta.label: active_effective_queryset(model).count()
        for model in Command.REQUIRED_MODELS
    }

    assert second_counts == first_counts


@pytest.mark.django_db
def test_complete_seed_has_active_rating_rider_fund_and_questionnaire_dependencies():
    call_command("seed_zanzibar_ol_complete", verbosity=0)

    premium_table = active_effective_queryset(OLPremiumRateTable).filter(
        plan__isnull=False,
        plan__is_active=True,
        rows__is_active=True,
    ).distinct()
    assert premium_table.exists()
    assert active_effective_queryset(OLPremiumRateRow).filter(
        table__in=premium_table,
        table__is_active=True,
    ).exists()

    mortality_table = active_effective_queryset(OLMortalityRateTable).filter(
        rows__is_active=True,
    ).distinct()
    assert mortality_table.exists()
    assert active_effective_queryset(OLMortalityRateRow).filter(
        table__in=mortality_table,
        table__is_active=True,
    ).exists()

    rider_table = active_effective_queryset(OLRiderRateTable).filter(
        rider__is_active=True,
        rows__is_active=True,
    ).distinct()
    assert rider_table.exists()
    assert active_effective_queryset(OLRiderRateRow).filter(
        table__in=rider_table,
        table__is_active=True,
    ).exists()
    assert active_effective_queryset(OLRiderSetup).exists()

    assert active_effective_queryset(OLInvestmentFund).filter(
        fund_type__is_active=True,
    ).exists()
    assert active_effective_queryset(OLHealthQuestionnaireItem).filter(
        questionnaire__is_active=True,
        health_question__is_active=True,
    ).exists()


@pytest.mark.django_db
def test_complete_seed_populates_every_quotation_option_with_human_labels():
    call_command("seed_zanzibar_ol_complete", verbosity=0)
    admin = User.objects.create_superuser(
        username="zic-complete-seed-options-admin",
        email="zic-complete-seed-options-admin@example.com",
        password="Strong-pass-123!",
    )
    client = APIClient()
    client.force_authenticate(admin)

    for entity in OPTION_ENTITIES:
        response = client.get(f"/api/v1/ol/options/{entity}/", {"page_size": 200})
        assert response.status_code == 200, (entity, response.data)
        assert response.data["success"] is True
        payload = response.data["data"]
        items = payload.get("items", payload.get("results", []))
        assert payload["count"] > 0, entity
        assert items, entity
        for option in items:
            assert option["value"]
            assert option["label"]
            assert isinstance(option["meta"], dict)
            assert option["label"] != str(option["value"]), entity


def test_complete_seed_command_exposes_non_destructive_verify_mode():
    assert any(argument.dest == "verify_only" for argument in Command().create_parser("manage.py", "seed_zanzibar_ol_complete")._actions)

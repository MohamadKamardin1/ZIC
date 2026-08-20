import pytest
from django.core.management import call_command

from apps.ol_parameters.models import (
    OLInvestmentFund,
    OLProduct,
    OLPremiumRateRow,
    OLPremiumRateTable,
    OLRiderRateRow,
    OLRiderRateTable,
    OLRiderSetup,
)
from apps.ordinary_life.models import OLPlan, OLProductVersion
from apps.partner_onboarding.models import Branch, Location


@pytest.mark.django_db
def test_zanzibar_ol_demo_seed_is_idempotent_and_quotation_ready():
    call_command("seed_zanzibar_ol_demo", verbosity=0)
    first_counts = {
        "products": OLProduct.objects.filter(code__in=["OL_TERM_LIFE", "OL_EDUCATION_SAVINGS", "OL_INVESTMENT_LINKED"]).count(),
        "versions": OLProductVersion.objects.filter(product__code__in=["OL_TERM_LIFE", "OL_EDUCATION_SAVINGS", "OL_INVESTMENT_LINKED"], is_active=True).count(),
        "plans": OLPlan.objects.filter(product_version__product__code__in=["OL_TERM_LIFE", "OL_EDUCATION_SAVINGS", "OL_INVESTMENT_LINKED"], is_active=True).count(),
        "riders": OLRiderSetup.objects.filter(code__startswith="ZIC_", is_active=True).count(),
        "funds": OLInvestmentFund.objects.filter(code__startswith="ZIC_", is_active=True).count(),
        "premium_tables": OLPremiumRateTable.objects.filter(table_code__startswith="ZIC_", is_active=True).count(),
        "premium_rows": OLPremiumRateRow.objects.filter(code__startswith="ZIC_", is_active=True).count(),
        "rider_rate_tables": OLRiderRateTable.objects.filter(table_code__startswith="ZIC_", is_active=True).count(),
        "rider_rate_rows": OLRiderRateRow.objects.filter(code__startswith="ZIC_", is_active=True).count(),
        "branches": Branch.objects.filter(code__startswith="ZIC-", is_active=True).count(),
        "locations": Location.objects.filter(branch__code__startswith="ZIC-", is_active=True).count(),
    }

    call_command("seed_zanzibar_ol_demo", verbosity=0)
    second_counts = {
        "products": OLProduct.objects.filter(code__in=["OL_TERM_LIFE", "OL_EDUCATION_SAVINGS", "OL_INVESTMENT_LINKED"]).count(),
        "versions": OLProductVersion.objects.filter(product__code__in=["OL_TERM_LIFE", "OL_EDUCATION_SAVINGS", "OL_INVESTMENT_LINKED"], is_active=True).count(),
        "plans": OLPlan.objects.filter(product_version__product__code__in=["OL_TERM_LIFE", "OL_EDUCATION_SAVINGS", "OL_INVESTMENT_LINKED"], is_active=True).count(),
        "riders": OLRiderSetup.objects.filter(code__startswith="ZIC_", is_active=True).count(),
        "funds": OLInvestmentFund.objects.filter(code__startswith="ZIC_", is_active=True).count(),
        "premium_tables": OLPremiumRateTable.objects.filter(table_code__startswith="ZIC_", is_active=True).count(),
        "premium_rows": OLPremiumRateRow.objects.filter(code__startswith="ZIC_", is_active=True).count(),
        "rider_rate_tables": OLRiderRateTable.objects.filter(table_code__startswith="ZIC_", is_active=True).count(),
        "rider_rate_rows": OLRiderRateRow.objects.filter(code__startswith="ZIC_", is_active=True).count(),
        "branches": Branch.objects.filter(code__startswith="ZIC-", is_active=True).count(),
        "locations": Location.objects.filter(branch__code__startswith="ZIC-", is_active=True).count(),
    }

    assert first_counts == second_counts
    assert first_counts["products"] == 3
    assert first_counts["versions"] == 3
    assert first_counts["plans"] == 6
    assert first_counts["riders"] == 6
    assert first_counts["funds"] == 3
    assert first_counts["premium_tables"] == 6
    assert first_counts["premium_rows"] == 432
    assert first_counts["rider_rate_tables"] == 6
    assert first_counts["rider_rate_rows"] == 432
    assert first_counts["branches"] == 4
    assert first_counts["locations"] == 17

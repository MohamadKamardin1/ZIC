"""Dashboard KPI hook for OL Proposals.

A clean seam the dashboard module can import: role-filtered, read-only counts
for the proposal register. All values are withheld as zeros for actors without
the OL proposals view role.
"""

from apps.ol_proposals.services.listing_service import proposal_kpis

DASHBOARD_KPI_KEYS = (
    "awaiting_first_premium",
    "awaiting_first_premium_amount",
    "expiring_in_7_days",
    "pending_underwriting",
)


def proposal_dashboard_kpis(user=None, *, as_of=None):
    """Return the dashboard subset of the register KPIs for a user."""
    full = proposal_kpis(user=user, as_of=as_of)
    return {key: full[key] for key in DASHBOARD_KPI_KEYS}
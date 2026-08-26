from django.core.cache import cache
from django.db.models.signals import post_delete, post_save

from apps.ol_parameters.models import OLLoanInterestControl, OLLoanSystemSetup

CACHE_REVISION_KEY = "ol_loans:parameter-config:revision"


def parameter_cache_revision():
    return int(cache.get(CACHE_REVISION_KEY, 1) or 1)


def invalidate_parameter_cache(sender=None, instance=None, **kwargs):
    """Bump the shared revision so all resolver keys become stale atomically."""
    try:
        revision = parameter_cache_revision()
        cache.set(CACHE_REVISION_KEY, revision + 1, timeout=None)
    except Exception:
        # Cache availability must never block a parameter write or loan action.
        cache.set(CACHE_REVISION_KEY, 1, timeout=None)


def register_parameter_cache_receivers():
    for model in (OLLoanSystemSetup, OLLoanInterestControl):
        post_save.connect(
            invalidate_parameter_cache,
            sender=model,
            dispatch_uid=f"ol_loans_{model.__name__.lower()}_cache_save",
        )
        post_delete.connect(
            invalidate_parameter_cache,
            sender=model,
            dispatch_uid=f"ol_loans_{model.__name__.lower()}_cache_delete",
        )

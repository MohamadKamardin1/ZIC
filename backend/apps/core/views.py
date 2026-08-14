import logging
from datetime import UTC, datetime

from django.conf import settings
from django.core.cache import cache
from django.db import connections
from django.http import JsonResponse
from django.views.decorators.http import require_GET

logger = logging.getLogger("apps.core.views")


def _timestamp():
    return datetime.now(UTC).isoformat()


def _service_result(name, check):
    try:
        check()
        return {"name": name, "status": "ready"}
    except Exception as exc:  # pragma: no cover - exact driver errors vary by environment
        logger.exception("Health dependency check failed: %s", name)
        return {"name": name, "status": "unavailable", "detail": str(exc)}


@require_GET
def liveness_check(request):
    """Process liveness probe that does not depend on external services."""
    return JsonResponse(
        {
            "status": "alive",
            "version": getattr(settings, "ZIC_RELEASE_VERSION", "1.0.0"),
            "timestamp": _timestamp(),
            "request_id": getattr(request, "request_id", None),
        },
        status=200,
    )


@require_GET
def readiness_check(request):
    """Readiness probe for database and configured cache dependencies."""
    services = [
        _service_result("database", lambda: connections["default"].ensure_connection()),
    ]
    if getattr(settings, "CACHES", None):
        services.append(_service_result("cache", lambda: cache.set("zic:readiness", "ok", 5)))
    ready = all(service["status"] == "ready" for service in services)
    return JsonResponse(
        {
            "status": "ready" if ready else "not_ready",
            "version": getattr(settings, "ZIC_RELEASE_VERSION", "1.0.0"),
            "services": services,
            "timestamp": _timestamp(),
            "request_id": getattr(request, "request_id", None),
        },
        status=200 if ready else 503,
    )


@require_GET
def health_check(request):
    """Backward-compatible health response retained for existing clients."""
    database = _service_result("database", lambda: connections["default"].ensure_connection())
    cache_service = _service_result("cache", lambda: cache.set("zic:health", "ok", 5))
    database_status = "connected" if database["status"] == "ready" else database.get("detail", "unavailable")
    cache_status = "connected" if cache_service["status"] == "ready" else cache_service.get("detail", "unavailable")
    return JsonResponse(
        {
            "status": "healthy" if database["status"] == "ready" else "degraded",
            "version": getattr(settings, "ZIC_RELEASE_VERSION", "1.0.0"),
            "services": {
                "database": database_status,
                "cache": cache_status,
                "redis": "not_checked",
            },
            "timestamp": _timestamp(),
            "request_id": getattr(request, "request_id", None),
        },
        status=200 if database["status"] == "ready" else 503,
    )

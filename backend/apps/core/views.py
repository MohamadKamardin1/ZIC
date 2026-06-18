import logging
from datetime import datetime

from django.db import connections
from django.http import JsonResponse
from django.conf import settings

logger = logging.getLogger('apps.core.views')


def health_check(request):
    db_status = 'connected'
    redis_status = 'disconnected'
    cache_status = 'disconnected'

    try:
        connections['default'].cursor()
    except Exception as e:
        db_status = f'error: {str(e)}'
        logger.error(f'Database health check failed: {str(e)}')

    try:
        import redis
        r = redis.from_url(settings.CELERY_BROKER_URL)
        r.ping()
        redis_status = 'connected'
    except Exception as e:
        redis_status = f'error: {str(e)}'

    response = {
        'status': 'healthy' if db_status == 'connected' else 'degraded',
        'version': '1.0.0',
        'services': {
            'database': db_status,
            'redis': redis_status,
            'cache': cache_status,
        },
        'timestamp': datetime.now().isoformat() + 'Z',
    }

    status_code = 200 if db_status == 'connected' else 503
    return JsonResponse(response, status=status_code)

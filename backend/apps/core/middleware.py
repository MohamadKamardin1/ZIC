import logging
import time
import uuid

from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin

from apps.core.logging import RequestLogger

request_logger = RequestLogger()
logger = logging.getLogger('apps.core.middleware')


class UniqueRequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.request_id = request.META.get(
            'HTTP_X_REQUEST_ID',
            f'req_{uuid.uuid4().hex[:12]}'
        )

    def process_response(self, request, response):
        if hasattr(request, 'request_id'):
            response['X-Request-ID'] = request.request_id
        return response


class RequestLoggingMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request._start_time = time.time()

    def process_response(self, request, response):
        if hasattr(request, '_start_time'):
            duration = time.time() - request._start_time
            request_id = getattr(request, 'request_id', None)
            request_logger.log_request(request, response, duration, request_id)
        return response

    def process_exception(self, request, exception):
        if hasattr(request, '_start_time'):
            request_id = getattr(request, 'request_id', None)
            request_logger.log_error(request, exception, request_id)


class UserActivityMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.user.is_authenticated:
            from apps.users.models import User
            User.objects.filter(id=request.user.id).update(
                last_activity=timezone.now(),
                last_ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255],
            )

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR')

import logging

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import exception_handler

logger = logging.getLogger('apps.core.exceptions')


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None:
        errors = response.data
        response.data = {
            'success': False,
            'status_code': response.status_code,
            'error': {
                'code': _get_error_code(response.status_code),
                'message': str(exc) if hasattr(exc, 'detail') else str(exc),
                'details': errors,
            },
            'meta': {
                'timestamp': __import__('datetime').datetime.now().isoformat() + 'Z',
                'request_id': _get_request_id(context.get('request')),
                'version': 'v1',
            },
        }
    else:
        logger.exception(f'Unhandled exception: {str(exc)}')
        response = Response(
            {
                'success': False,
                'status_code': status.HTTP_500_INTERNAL_SERVER_ERROR,
                'error': {
                    'code': 'INTERNAL_SERVER_ERROR',
                    'message': 'An unexpected error occurred.',
                    'details': None,
                },
                'meta': {
                    'timestamp': __import__('datetime').datetime.now().isoformat() + 'Z',
                    'request_id': _get_request_id(context.get('request')),
                    'version': 'v1',
                },
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return response


def _get_error_code(status_code):
    codes = {
        400: 'VALIDATION_ERROR',
        401: 'UNAUTHORIZED',
        403: 'FORBIDDEN',
        404: 'NOT_FOUND',
        405: 'METHOD_NOT_ALLOWED',
        409: 'CONFLICT',
        429: 'RATE_LIMITED',
        500: 'INTERNAL_SERVER_ERROR',
        502: 'BAD_GATEWAY',
        503: 'SERVICE_UNAVAILABLE',
    }
    return codes.get(status_code, 'UNKNOWN_ERROR')


def _get_request_id(request):
    if request and hasattr(request, 'request_id'):
        return request.request_id
    return None


class ZICAPIException(Exception):
    def __init__(self, message, code='ERROR', status_code=400, details=None):
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details
        super().__init__(self.message)

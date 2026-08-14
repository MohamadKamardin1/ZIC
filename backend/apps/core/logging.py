import logging
from datetime import datetime


class ZICLogFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[36m',
        'INFO': '\033[32m',
        'WARNING': '\033[33m',
        'ERROR': '\033[31m',
        'CRITICAL': '\033[41m',
    }
    RESET = '\033[0m'
    BOLD = '\033[1m'

    def format(self, record):
        timestamp = datetime.fromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        level = record.levelname
        color = self.COLORS.get(level, '')
        module = record.name
        msg = record.getMessage()

        log_line = (
            f'{self.BOLD}[{timestamp}]{self.RESET} '
            f'{color}[{level}]{self.RESET} '
            f'\033[35m[{module}]\033[0m '
            f'{color}{msg}{self.RESET}'
        )
        return log_line


class RequestLogger:
    def __init__(self):
        self.logger = logging.getLogger('apps.core.request')

    def log_request(self, request, response, duration, request_id=None):
        user = getattr(request, 'user', None)
        user_str = str(user) if user and user.is_authenticated else 'anonymous'

        self.logger.info(
            f'[{request_id}] {request.method} {request.path} '
            f'-> {response.status_code} ({duration:.2f}s) '
            f'[{user_str}]'
        )

    def log_error(self, request, error, request_id=None):
        user = getattr(request, 'user', None)
        user_str = str(user) if user and user.is_authenticated else 'anonymous'

        self.logger.error(
            f'[{request_id}] {request.method} {request.path} '
            f'ERROR: {str(error)} [{user_str}]'
        )

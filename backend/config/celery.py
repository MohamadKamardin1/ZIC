import os
import logging

from celery import Celery
from django.conf import settings

logger = logging.getLogger('config.celery')

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('zic')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    logger.info(f'Celery task: {self.request!r}')

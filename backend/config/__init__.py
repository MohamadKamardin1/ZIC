from .patches import apply_patches
apply_patches()

from .celery import app as celery_app

__all__ = ('celery_app',)

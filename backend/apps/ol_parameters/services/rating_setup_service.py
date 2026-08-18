from django.db import transaction

from .default_setup_service import OLDefaultSetupService


class OLRatingSetupService:
    """Application services for bulk-safe Product Rating parameter operations."""

    @classmethod
    @transaction.atomic
    def bulk_create_rows(cls, *, model, actor, rows, request=None):
        """Create validated rating rows atomically and audit each material mutation."""
        return [
            OLDefaultSetupService.create(
                model=model,
                actor=actor,
                data=row,
                request=request,
            )
            for row in rows
        ]

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.ol_parameters.models import OLProposalDocumentRequirement


def _requirements():
    return [
        {"code": "PROPOSAL_DOC_IDENTITY", "name": "Identity Document", "document_type": "IDENTITY_DOCUMENT", "mandatory": True},
        {"code": "PROPOSAL_DOC_SIGNATURE", "name": "Signature", "document_type": "SIGNATURE", "mandatory": True},
        {"code": "PROPOSAL_DOC_KYC", "name": "KYC Form", "document_type": "KYC_FORM", "mandatory": True},
    ]


class Command(BaseCommand):
    help = "Seed default OL Proposal document requirements (identity, signature, KYC)."

    @transaction.atomic
    def handle(self, *args, **options):
        for payload in _requirements():
            OLProposalDocumentRequirement.objects.update_or_create(
                code=payload["code"],
                defaults={
                    "name": payload["name"],
                    "description": f"Mandatory proposal document: {payload['name']}.",
                    "document_type": payload["document_type"],
                    "mandatory": payload["mandatory"],
                    "product": None,
                    "plan": None,
                    "effective_from": date(2020, 1, 1),
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(_requirements())} proposal document requirements."))
from django.core.management import call_command
from django.test import TestCase

from apps.ol_proposals.permissions import ACTIONS, OLProposalPermission
from apps.users.models import PermissionGroup, UserGroup, UserPermission


class OLProposalPermissionTests(TestCase):
    def test_seed_registers_all_permissions(self):
        call_command("seed_ol_proposal_permissions")
        for action in ACTIONS:
            self.assertTrue(
                UserPermission.objects.filter(
                    codename=f"ol_proposals.{action}", module="ol_proposals", action=action.upper(), is_active=True
                ).exists(),
                f"missing ol_proposals.{action}",
            )

    def test_seed_creates_group_and_roles(self):
        call_command("seed_ol_proposal_permissions")
        self.assertTrue(PermissionGroup.objects.filter(module_code="OL_PROPOSALS").exists())
        for code in ("OL_PROPOSAL_VIEWER", "OL_PROPOSAL_HANDLER", "OL_PROPOSAL_ADMINISTRATOR"):
            group = UserGroup.objects.get(code=code)
            self.assertTrue(group.permissions.filter(codename="ol_proposals.view").exists())

    def test_action_to_code_mapping(self):
        self.assertEqual(OLProposalPermission.code_for("mark_payment_ready"), "ol_proposals.mark_payment_ready")
        self.assertEqual(OLProposalPermission.code_for("convert"), "ol_proposals.convert")
        self.assertEqual(OLProposalPermission.code_for("enrich"), "ol_proposals.enrich")
        self.assertEqual(OLProposalPermission.code_for("view"), "ol_proposals.view")
        self.assertEqual(OLProposalPermission.code_for("unknown"), "ol_proposals.view")
        self.assertIn("print", ACTIONS)
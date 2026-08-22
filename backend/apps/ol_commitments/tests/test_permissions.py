from django.core.management import call_command
from django.test import TestCase

from apps.ol_commitments.permissions import ACTIONS, OLCommitmentPermission
from apps.users.models import PermissionGroup, UserGroup, UserPermission


class OLCommitmentPermissionRegistrationTests(TestCase):
    def test_permission_codes_are_registered_by_seed_command(self):
        call_command("seed_ol_commitment_permissions")
        for action in ACTIONS:
            self.assertTrue(
                UserPermission.objects.filter(
                    codename=f"ol_commitments.{action}",
                    module="ol_commitments",
                    action=action.upper(),
                    is_active=True,
                ).exists(),
                f"permission ol_commitments.{action} was not seeded",
            )
        self.assertEqual(UserPermission.objects.filter(module="ol_commitments").count(), len(ACTIONS))

    def test_allowed_codes_match_action_tuple(self):
        self.assertEqual(
            set(OLCommitmentPermission.allowed_codes()),
            {f"ol_commitments.{action}" for action in ACTIONS},
        )
        self.assertIn("record_payment", ACTIONS)

    def test_seed_creates_permission_group_and_role_groups(self):
        call_command("seed_ol_commitment_permissions")
        self.assertTrue(PermissionGroup.objects.filter(module_code="OL_COMMITMENTS").exists())
        for code in ("OL_COMMITMENT_VIEWER", "OL_COMMITMENT_HANDLER", "OL_COMMITMENT_ADMINISTRATOR"):
            group = UserGroup.objects.get(code=code)
            self.assertTrue(group.permissions.filter(codename="ol_commitments.view").exists())

    def test_action_to_code_mapping(self):
        self.assertEqual(OLCommitmentPermission.code_for("record_payment"), "ol_commitments.record_payment")
        self.assertEqual(OLCommitmentPermission.code_for("generate"), "ol_commitments.generate")
        self.assertEqual(OLCommitmentPermission.code_for("list"), "ol_commitments.view")
        self.assertEqual(OLCommitmentPermission.code_for("unknown"), "ol_commitments.view")

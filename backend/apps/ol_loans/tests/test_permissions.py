from django.core.management import call_command
from django.test import TestCase

from apps.ol_loans.permissions import ACTIONS, OLLoanPermission
from apps.users.models import PermissionGroup, UserGroup, UserPermission


class OLLoanPermissionTestCase(TestCase):
    def test_permission_codes_are_registered_in_the_module_contract(self):
        self.assertEqual(
            OLLoanPermission.allowed_codes(),
            tuple(f"ol_loans.{action}" for action in ACTIONS),
        )
        self.assertEqual(OLLoanPermission.code_for("list"), "ol_loans.view")
        self.assertEqual(OLLoanPermission.code_for("request"), "ol_loans.request")
        self.assertEqual(OLLoanPermission.code_for("configure"), "ol_loans.configure")

    def test_permission_seeder_creates_permissions_group_and_roles(self):
        call_command("seed_ol_loan_permissions")
        self.assertEqual(UserPermission.objects.filter(module="ol_loans", is_active=True).count(), len(ACTIONS))
        permission_group = PermissionGroup.objects.get(module_code="OL_LOANS")
        self.assertEqual(permission_group.permissions.count(), len(ACTIONS))
        administrator = UserGroup.objects.get(code="OL_LOAN_ADMINISTRATOR")
        self.assertEqual(administrator.permissions.count(), len(ACTIONS))

        call_command("seed_ol_loan_permissions", verbosity=0)
        self.assertEqual(UserPermission.objects.filter(module="ol_loans", is_active=True).count(), len(ACTIONS))

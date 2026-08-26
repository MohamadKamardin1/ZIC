from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase

from apps.front_office.receipts.permissions import ACTIONS, RECEIPTS_MODULE, ReceiptPermission, has_receipt_permission
from apps.users.models import PermissionGroup, UserGroup, UserPermission

User = get_user_model()


class ReceiptPermissionRegistrationTests(TestCase):
    def test_permission_codes_are_registered_by_seed_command(self):
        call_command("seed_receipt_permissions")
        for action in ACTIONS:
            self.assertTrue(
                UserPermission.objects.filter(
                    codename=f"{RECEIPTS_MODULE}.{action}",
                    module=RECEIPTS_MODULE,
                    action=action.upper(),
                    is_active=True,
                ).exists(),
                f"permission {RECEIPTS_MODULE}.{action} was not seeded",
            )
        self.assertEqual(UserPermission.objects.filter(module=RECEIPTS_MODULE).count(), len(ACTIONS))

    def test_required_permissions_present(self):
        call_command("seed_receipt_permissions")
        for code in (
            "front_office.receipts.view",
            "front_office.receipts.create",
            "front_office.receipts.post",
            "front_office.receipts.allocate",
            "front_office.receipts.reverse",
            "front_office.receipts.cancel",
            "front_office.receipts.print",
            "front_office.receipts.import",
            "front_office.receipts.configure",
        ):
            self.assertTrue(UserPermission.objects.filter(codename=code).exists(), f"missing {code}")

    def test_allowed_codes_match_action_tuple(self):
        self.assertEqual(
            set(ReceiptPermission.allowed_codes()),
            {f"{RECEIPTS_MODULE}.{action}" for action in ACTIONS},
        )
        self.assertIn("post", ACTIONS)
        self.assertIn("allocate", ACTIONS)

    def test_seed_creates_permission_group_and_role_groups(self):
        call_command("seed_receipt_permissions")
        self.assertTrue(PermissionGroup.objects.filter(module_code="FRONT_OFFICE_RECEIPTS").exists())
        for code in ("RECEIPT_VIEWER", "RECEIPT_HANDLER", "RECEIPT_ADMINISTRATOR"):
            group = UserGroup.objects.get(code=code)
            self.assertTrue(group.permissions.filter(codename="front_office.receipts.view").exists())

    def test_action_to_code_mapping(self):
        self.assertEqual(ReceiptPermission.code_for("post"), "front_office.receipts.post")
        self.assertEqual(ReceiptPermission.code_for("allocate"), "front_office.receipts.allocate")
        self.assertEqual(ReceiptPermission.code_for("list"), "front_office.receipts.view")
        self.assertEqual(ReceiptPermission.code_for("update"), "front_office.receipts.create")


class HasReceiptPermissionTests(TestCase):
    def setUp(self):
        call_command("seed_receipt_permissions")
        self.superuser = User.objects.create_superuser(
            username="root", password="Password@12345", email="root@zic.tz"
        )
        self.plain = User.objects.create_user(username="plain", password="Password@12345", email="plain@zic.tz")
        self.handler = User.objects.create_user(username="handler", password="Password@12345", email="handler@zic.tz")
        UserGroup.objects.get(code="RECEIPT_HANDLER").users.add(self.handler)

    def test_superuser_bypasses(self):
        self.assertTrue(has_receipt_permission(self.superuser, "reverse"))

    def test_plain_user_denied(self):
        self.assertFalse(has_receipt_permission(self.plain, "view"))
        self.assertFalse(has_receipt_permission(self.plain, "post"))

    def test_handler_has_create_and_view(self):
        self.assertTrue(has_receipt_permission(self.handler, "view"))
        self.assertTrue(has_receipt_permission(self.handler, "create"))
        self.assertTrue(has_receipt_permission(self.handler, "post"))
        self.assertFalse(has_receipt_permission(self.handler, "reverse"))

    def test_anonymous_denied(self):
        anon = User()
        self.assertFalse(has_receipt_permission(anon, "view"))
        self.assertFalse(has_receipt_permission(None, "view"))

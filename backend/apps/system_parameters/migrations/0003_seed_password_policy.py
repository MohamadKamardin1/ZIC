"""Seed password policy group and parameters."""

from django.db import migrations


def seed_password_policy(apps, schema_editor):
    ParameterGroup = apps.get_model("system_parameters", "ParameterGroup")
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")

    users_group = ParameterGroup.objects.get(code="USERS")

    # Create Password Policy group as child of USERS
    password_policy = ParameterGroup.objects.create(
        parent=users_group,
        code="PASSWORD_POLICY",
        name="Password Policy",
        description="Password complexity rules, expiry, history, and lockout settings",
        sort_order=10,
    )

    # Seed general user settings under USERS group
    SystemParameter.objects.create(
        group=users_group, code="SESSION_TIMEOUT_MINUTES", name="Session Timeout (minutes)",
        value_type="INTEGER", integer_value=30,
        description="Idle session timeout in minutes",
        sort_order=10,
    )
    SystemParameter.objects.create(
        group=users_group, code="MAX_LOGIN_ATTEMPTS", name="Max Login Attempts",
        value_type="INTEGER", integer_value=5,
        description="Maximum failed login attempts before account lockout",
        sort_order=20,
    )
    SystemParameter.objects.create(
        group=users_group, code="LOCKOUT_DURATION_MINUTES", name="Lockout Duration (minutes)",
        value_type="INTEGER", integer_value=30,
        description="Duration in minutes for which an account is locked after too many failed attempts",
        sort_order=30,
    )
    SystemParameter.objects.create(
        group=users_group, code="TWO_FACTOR_REQUIRED", name="Require 2FA",
        value_type="BOOLEAN", boolean_value=False,
        description="Whether two-factor authentication is required for all users",
        sort_order=40,
    )
    SystemParameter.objects.create(
        group=users_group, code="ALLOW_SELF_REGISTRATION", name="Allow Self-Registration",
        value_type="BOOLEAN", boolean_value=False,
        description="Whether users can register themselves without admin approval",
        sort_order=50,
    )
    SystemParameter.objects.create(
        group=users_group, code="DEFAULT_USER_ROLE", name="Default User Role",
        value_type="STRING", string_value="viewer",
        description="Default role assigned to newly created users",
        sort_order=60,
    )

    # Seed password policy parameters under PASSWORD_POLICY group
    SystemParameter.objects.create(
        group=password_policy, code="MIN_LENGTH", name="Minimum Password Length",
        value_type="INTEGER", integer_value=8,
        description="Minimum number of characters required for passwords",
        sort_order=10,
    )
    SystemParameter.objects.create(
        group=password_policy, code="MAX_LENGTH", name="Maximum Password Length",
        value_type="INTEGER", integer_value=128,
        description="Maximum number of characters allowed for passwords",
        sort_order=20,
    )
    SystemParameter.objects.create(
        group=password_policy, code="REQUIRE_UPPERCASE", name="Require Uppercase Letter",
        value_type="BOOLEAN", boolean_value=True,
        description="Passwords must contain at least one uppercase letter",
        sort_order=30,
    )
    SystemParameter.objects.create(
        group=password_policy, code="REQUIRE_LOWERCASE", name="Require Lowercase Letter",
        value_type="BOOLEAN", boolean_value=True,
        description="Passwords must contain at least one lowercase letter",
        sort_order=40,
    )
    SystemParameter.objects.create(
        group=password_policy, code="REQUIRE_DIGIT", name="Require Digit",
        value_type="BOOLEAN", boolean_value=True,
        description="Passwords must contain at least one digit",
        sort_order=50,
    )
    SystemParameter.objects.create(
        group=password_policy, code="REQUIRE_SPECIAL_CHAR", name="Require Special Character",
        value_type="BOOLEAN", boolean_value=False,
        description="Passwords must contain at least one special character",
        sort_order=60,
    )
    SystemParameter.objects.create(
        group=password_policy, code="SPECIAL_CHARACTER_SET", name="Allowed Special Characters",
        value_type="STRING", string_value="!@#$%^&*()_+-=[]{}|;':\",./<>?`~",
        description="Set of special characters that are allowed in passwords",
        sort_order=70,
    )
    SystemParameter.objects.create(
        group=password_policy, code="EXPIRY_DAYS", name="Password Expiry (days)",
        value_type="INTEGER", integer_value=90,
        description="Number of days after which a password must be changed",
        sort_order=80,
    )
    SystemParameter.objects.create(
        group=password_policy, code="HISTORY_COUNT", name="Password History Count",
        value_type="INTEGER", integer_value=5,
        description="Number of previous passwords to remember and prevent reuse",
        sort_order=90,
    )
    SystemParameter.objects.create(
        group=password_policy, code="MIN_PASSWORD_AGE_HOURS", name="Minimum Password Age (hours)",
        value_type="INTEGER", integer_value=1,
        description="Minimum hours before a password can be changed again",
        sort_order=100,
    )
    SystemParameter.objects.create(
        group=password_policy, code="NOTIFY_ON_CHANGE", name="Notify on Password Change",
        value_type="BOOLEAN", boolean_value=True,
        description="Send email notification when password is changed",
        sort_order=110,
    )


def reverse_password_policy(apps, schema_editor):
    ParameterGroup = apps.get_model("system_parameters", "ParameterGroup")
    SystemParameter = apps.get_model("system_parameters", "SystemParameter")
    SystemParameter.objects.filter(group__code__in=["USERS", "PASSWORD_POLICY"]).delete()
    try:
        pp = ParameterGroup.objects.get(code="PASSWORD_POLICY")
        pp.delete()
    except ParameterGroup.DoesNotExist:
        pass


class Migration(migrations.Migration):
    dependencies = [
        ("system_parameters", "0002_seed_initial_data"),
    ]
    operations = [
        migrations.RunPython(seed_password_policy, reverse_password_policy),
    ]

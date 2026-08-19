from django.contrib.auth import get_user_model

User = get_user_model()
username = "zic_local_superadmin"
email = "zic_local_superadmin@localhost.test"
password = "ZicLocalSuperadmin!2026"

user, created = User.objects.get_or_create(
    username=username,
    defaults={
        "email": email,
        "first_name": "ZIC",
        "last_name": "Local Superadmin",
        "user_type": "SUPER_ADMIN",
        "status": "ACTIVE",
        "is_active": True,
        "is_staff": True,
        "is_superuser": True,
        "is_approved": True,
        "email_verified": True,
        "must_change_password": False,
    },
)

user.email = email
user.user_type = "SUPER_ADMIN"
user.status = "ACTIVE"
user.is_active = True
user.is_staff = True
user.is_superuser = True
user.is_approved = True
user.email_verified = True
user.must_change_password = False
user.set_password(password)
user.save()

print({"username": username, "email": email, "created": created, "is_superuser": user.is_superuser, "is_active": user.is_active})

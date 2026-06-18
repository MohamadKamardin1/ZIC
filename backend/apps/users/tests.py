import pytest
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.utils import timezone
from datetime import timedelta


class UserModelTests(TestCase):
    def setUp(self):
        from apps.users.models import User
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='TestPass123!',
            first_name='Test',
            last_name='User',
        )

    def test_create_user(self):
        from apps.users.models import User
        user = User.objects.create_user(
            username='testuser2',
            email='test2@example.com',
            password='TestPass123!',
        )
        self.assertEqual(user.username, 'testuser2')
        self.assertEqual(user.email, 'test2@example.com')
        self.assertTrue(user.check_password('TestPass123!'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        from apps.users.models import User
        admin = User.objects.create_superuser(
            username='admin2',
            email='admin2@example.com',
            password='AdminPass123!',
        )
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertEqual(admin.user_type, 'SUPER_ADMIN')

    def test_user_str(self):
        self.assertEqual(str(self.user), 'testuser (test@example.com)')

    def test_full_name(self):
        self.assertEqual(self.user.full_name, 'Test User')

    def test_account_locking(self):
        self.assertFalse(self.user.is_account_locked)
        self.user.account_locked_until = timezone.now() - timedelta(minutes=5)
        self.user.save()
        self.assertFalse(self.user.is_account_locked)
        self.user.account_locked_until = timezone.now() + timedelta(minutes=15)
        self.user.save()
        self.assertTrue(self.user.is_account_locked)

    def test_failed_login_tracking(self):
        self.assertEqual(self.user.failed_login_attempts, 0)
        for _ in range(4):
            self.user.record_failed_login()
        self.assertEqual(self.user.failed_login_attempts, 4)
        self.assertFalse(self.user.is_account_locked)
        self.user.record_failed_login()
        self.assertEqual(self.user.failed_login_attempts, 5)
        self.assertTrue(self.user.is_account_locked)
        self.user.reset_failed_login()
        self.assertEqual(self.user.failed_login_attempts, 0)
        self.assertIsNone(self.user.account_locked_until)


class UserGroupModelTests(TestCase):
    def setUp(self):
        from apps.users.models import UserGroup, UserPermission
        self.group = UserGroup.objects.create(
            name='MANAGER',
            description='Manager group',
        )
        self.permission = UserPermission.objects.create(
            name='View Partners',
            codename='view_partner',
            module='PARTNER_MANAGEMENT',
            action='READ',
        )

    def test_create_group(self):
        self.assertEqual(self.group.name, 'MANAGER')
        self.assertTrue(self.group.is_system_group)

    def test_group_permissions(self):
        self.group.permissions.add(self.permission)
        self.assertEqual(self.group.permissions.count(), 1)


class UserOTPModelTests(TestCase):
    def setUp(self):
        from apps.users.models import User
        self.user = User.objects.create_user(
            username='otpuser',
            email='otp@example.com',
            password='TestPass123!',
        )

    def test_generate_otp(self):
        from apps.users.models import UserOTP
        otp = UserOTP.generate_otp(self.user, 'LOGIN')
        self.assertEqual(otp.user, self.user)
        self.assertEqual(otp.otp_type, 'LOGIN')
        self.assertFalse(otp.is_used)
        self.assertFalse(otp.is_expired)
        self.assertEqual(len(otp.otp_code), 6)
        self.assertTrue(otp.is_valid)

    def test_otp_expiry(self):
        from apps.users.models import UserOTP
        otp = UserOTP.objects.create(
            user=self.user,
            otp_code='123456',
            otp_type='LOGIN',
            expires_at=timezone.now() - timedelta(minutes=1),
        )
        self.assertTrue(otp.is_expired)
        self.assertFalse(otp.is_valid)

    def test_otp_used(self):
        from apps.users.models import UserOTP
        otp = UserOTP.generate_otp(self.user, 'LOGIN')
        otp.is_used = True
        otp.save()
        self.assertFalse(otp.is_valid)


class APITestCaseBase(APITestCase):
    def setUp(self):
        from apps.users.models import User
        self.client = APIClient()
        self.user = User.objects.create_superuser(
            username='apiadmin',
            email='apiadmin@example.com',
            password='AdminPass123!',
            first_name='API',
            last_name='Admin',
        )
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'apiadmin',
            'password': 'AdminPass123!',
        }, format='json')
        self.token = response.data['data']['access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.token}')


class HealthCheckTests(APITestCaseBase):
    def test_health_endpoint(self):
        response = self.client.get('/api/v1/health/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()['status'], 'healthy')

    def test_health_response_structure(self):
        response = self.client.get('/api/v1/health/')
        data = response.json()
        self.assertIn('services', data)
        self.assertIn('database', data['services'])
        self.assertIn('timestamp', data)


class AuthenticationAPITests(APITestCaseBase):
    def test_login_success(self):
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'apiadmin',
            'password': 'AdminPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['success'])
        self.assertIn('access_token', response.data['data'])
        self.assertIn('refresh_token', response.data['data'])
        self.assertIn('user', response.data['data'])

    def test_login_invalid_credentials(self):
        response = self.client.post('/api/v1/auth/login/', {
            'username': 'apiadmin',
            'password': 'wrongpassword',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_missing_fields(self):
        response = self.client.post('/api/v1/auth/login/', {}, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_register_user(self):
        response = self.client.post('/api/v1/auth/register/', {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'NewUserPass123!',
            'password_confirm': 'NewUserPass123!',
            'first_name': 'New',
            'last_name': 'User',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(response.data['success'])

    def test_token_refresh(self):
        login_resp = self.client.post('/api/v1/auth/login/', {
            'username': 'apiadmin',
            'password': 'AdminPass123!',
        }, format='json')
        refresh_token = login_resp.data['data']['refresh_token']
        response = self.client.post('/api/v1/auth/refresh/', {
            'refresh': refresh_token,
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class UserAPITests(APITestCaseBase):
    def setUp(self):
        from apps.users.models import User
        super().setUp()
        self.test_user = User.objects.create_user(
            username='regularuser',
            email='regular@example.com',
            password='TestPass123!',
            first_name='Regular',
            last_name='User',
        )

    def test_list_users(self):
        response = self.client.get('/api/v1/users/users/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)

    def test_get_user_detail(self):
        response = self.client.get(f'/api/v1/users/users/{self.test_user.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'regularuser')

    def test_get_my_profile(self):
        response = self.client.get('/api/v1/users/users/me/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['data']['username'], 'apiadmin')

    def test_update_profile(self):
        response = self.client.put('/api/v1/users/users/update_profile/', {
            'first_name': 'UpdatedName',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, 'UpdatedName')

    def test_change_password(self):
        response = self.client.post('/api/v1/users/users/change_password/', {
            'current_password': 'AdminPass123!',
            'new_password': 'NewAdminPass123!',
            'new_password_confirm': 'NewAdminPass123!',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('NewAdminPass123!'))
        self.user.set_password('AdminPass123!')
        self.user.save()


class PermissionAPITests(APITestCaseBase):
    def setUp(self):
        from apps.users.models import UserPermission
        super().setUp()
        self.permission = UserPermission.objects.create(
            name='Test Permission',
            codename='test_perm',
            module='TEST_MODULE',
            action='READ',
        )

    def test_list_permissions(self):
        response = self.client.get('/api/v1/users/permissions/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_list_modules(self):
        response = self.client.get('/api/v1/users/permissions/modules/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('TEST_MODULE', response.data['data'])


class UserGroupAPITests(APITestCaseBase):
    def setUp(self):
        from apps.users.models import UserGroup
        super().setUp()
        self.group = UserGroup.objects.create(
            name='PORTAL_USER',
            description='Test portal group',
        )

    def test_list_groups(self):
        response = self.client.get('/api/v1/users/groups/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_create_group(self):
        response = self.client.post('/api/v1/users/groups/', {
            'name': 'MANAGER',
            'description': 'New test group',
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_get_group_detail(self):
        response = self.client.get(f'/api/v1/users/groups/{self.group.id}/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)


class ResponseFormatTests(APITestCaseBase):
    def test_success_response_format(self):
        response = self.client.get('/api/v1/users/users/me/')
        self.assertIn('success', response.data)
        self.assertIn('status_code', response.data)
        self.assertIn('message', response.data)
        self.assertIn('data', response.data)
        self.assertIn('meta', response.data)

    def test_error_response_format(self):
        self.client.credentials()
        response = self.client.get('/api/v1/users/users/me/')
        self.assertIn('success', response.data)
        self.assertFalse(response.data['success'])
        self.assertIn('error', response.data)

"""Authorization tests: JWT + 2FA, role management and organization lifecycle."""

import pyotp
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from accounts.models import TwoFactorDevice, UserRole
from organizations.models import Organization

User = get_user_model()


class JwtAuthenticationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            email="jwt@namaa.sa", password="Str0ng!pass"
        )

    def test_register_creates_user_with_hashed_password(self):
        response = self.client.post(
            "/api/v1/auth/register/",
            {
                "email": "new@namaa.sa",
                "password": "Str0ng!pass123",
                "first_name": "Nora",
            },
        )
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(email="new@namaa.sa")
        self.assertTrue(user.check_password("Str0ng!pass123"))
        self.assertNotIn("password", response.data)

    def test_obtain_and_refresh_token_pair(self):
        response = self.client.post(
            "/api/v1/auth/token/", {"email": "jwt@namaa.sa", "password": "Str0ng!pass"}
        )
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)

        refresh = self.client.post(
            "/api/v1/auth/token/refresh/", {"refresh": response.data["refresh"]}
        )
        self.assertEqual(refresh.status_code, 200, refresh.data)
        self.assertIn("access", refresh.data)

    def test_access_token_authenticates_api_requests(self):
        token = self.client.post(
            "/api/v1/auth/token/", {"email": "jwt@namaa.sa", "password": "Str0ng!pass"}
        ).data["access"]
        response = self.client.get("/api/v1/me/", HTTP_AUTHORIZATION=f"Bearer {token}")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["email"], "jwt@namaa.sa")

    def test_blacklisted_refresh_token_is_rejected(self):
        pair = self.client.post(
            "/api/v1/auth/token/", {"email": "jwt@namaa.sa", "password": "Str0ng!pass"}
        ).data
        blacklist = self.client.post(
            "/api/v1/auth/token/blacklist/", {"refresh": pair["refresh"]}
        )
        self.assertEqual(blacklist.status_code, 200)
        refresh = self.client.post(
            "/api/v1/auth/token/refresh/", {"refresh": pair["refresh"]}
        )
        self.assertEqual(refresh.status_code, 401)


class TwoFactorAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email="2fa@namaa.sa", password="Str0ng!pass"
        )
        self.client.force_authenticate(self.user)

    def _enable_2fa(self):
        setup = self.client.post("/api/v1/auth/2fa/setup/")
        self.assertEqual(setup.status_code, 201, setup.data)
        secret = setup.data["secret"]
        verify = self.client.post(
            "/api/v1/auth/2fa/verify/", {"code": pyotp.TOTP(secret).now()}
        )
        self.assertEqual(verify.status_code, 200, verify.data)
        return secret

    def test_setup_returns_secret_and_provisioning_uri(self):
        response = self.client.post("/api/v1/auth/2fa/setup/")
        self.assertEqual(response.status_code, 201)
        self.assertIn("secret", response.data)
        self.assertTrue(response.data["otpauth_uri"].startswith("otpauth://totp/"))

    def test_verify_with_wrong_code_does_not_enable(self):
        self.client.post("/api/v1/auth/2fa/setup/")
        response = self.client.post("/api/v1/auth/2fa/verify/", {"code": "000000"})
        self.assertEqual(response.status_code, 400)
        self.assertFalse(TwoFactorDevice.objects.get(user=self.user).confirmed)

    def test_login_requires_otp_once_enabled(self):
        secret = self._enable_2fa()
        self.client.force_authenticate(None)

        without_otp = self.client.post(
            "/api/v1/auth/token/", {"email": "2fa@namaa.sa", "password": "Str0ng!pass"}
        )
        self.assertEqual(without_otp.status_code, 400)
        self.assertIn("otp_code", without_otp.data)

        with_otp = self.client.post(
            "/api/v1/auth/token/",
            {
                "email": "2fa@namaa.sa",
                "password": "Str0ng!pass",
                "otp_code": pyotp.TOTP(secret).now(),
            },
        )
        self.assertEqual(with_otp.status_code, 200, with_otp.data)
        self.assertIn("access", with_otp.data)

    def test_disable_requires_valid_code(self):
        secret = self._enable_2fa()
        rejected = self.client.post("/api/v1/auth/2fa/disable/", {"code": "000000"})
        self.assertEqual(rejected.status_code, 400)
        accepted = self.client.post(
            "/api/v1/auth/2fa/disable/", {"code": pyotp.TOTP(secret).now()}
        )
        self.assertEqual(accepted.status_code, 200)
        self.assertFalse(TwoFactorDevice.objects.filter(user=self.user).exists())


class RoleManagementAuthorizationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Salon A", slug="salon-a")

        cls.owner = User.objects.create_user(
            email="owner@namaa.sa", password="pass12345"
        )
        cls.admin = User.objects.create_user(
            email="admin@namaa.sa", password="pass12345"
        )
        cls.staff = User.objects.create_user(
            email="staff@namaa.sa", password="pass12345"
        )
        cls.newcomer = User.objects.create_user(
            email="new@namaa.sa", password="pass12345"
        )

        UserRole.objects.create(
            user=cls.owner, organization=cls.org, role=UserRole.Role.OWNER
        )
        cls.admin_role = UserRole.objects.create(
            user=cls.admin, organization=cls.org, role=UserRole.Role.ADMIN
        )
        cls.staff_role = UserRole.objects.create(
            user=cls.staff, organization=cls.org, role=UserRole.Role.STAFF
        )

    def _grant(self, user, target_user, role):
        self.client.force_authenticate(user)
        return self.client.post(
            "/api/v1/user-roles/",
            {
                "user": str(target_user.id),
                "organization": str(self.org.id),
                "role": role,
            },
        )

    def test_staff_cannot_grant_themselves_owner(self):
        response = self._grant(self.staff, self.staff, UserRole.Role.OWNER)
        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_grant_a_role_above_their_own(self):
        response = self._grant(self.admin, self.newcomer, UserRole.Role.OWNER)
        self.assertEqual(response.status_code, 403)

    def test_admin_can_grant_staff_role(self):
        response = self._grant(self.admin, self.newcomer, UserRole.Role.STAFF)
        self.assertEqual(response.status_code, 201, response.data)

    def test_owner_can_grant_admin_role(self):
        response = self._grant(self.owner, self.newcomer, UserRole.Role.ADMIN)
        self.assertEqual(response.status_code, 201, response.data)

    def test_admin_cannot_elevate_their_own_role(self):
        self.client.force_authenticate(self.admin)
        response = self.client.patch(
            f"/api/v1/user-roles/{self.admin_role.id}/",
            {"role": UserRole.Role.OWNER},
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_cannot_delete_role_rows(self):
        self.client.force_authenticate(self.staff)
        response = self.client.delete(f"/api/v1/user-roles/{self.admin_role.id}/")
        self.assertEqual(response.status_code, 403)


class OrganizationLifecycleAuthorizationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.org = Organization.objects.create(name="Salon A", slug="salon-a")
        cls.owner = User.objects.create_user(
            email="owner@namaa.sa", password="pass12345"
        )
        cls.staff = User.objects.create_user(
            email="staff@namaa.sa", password="pass12345"
        )
        UserRole.objects.create(
            user=cls.owner, organization=cls.org, role=UserRole.Role.OWNER
        )
        UserRole.objects.create(
            user=cls.staff, organization=cls.org, role=UserRole.Role.STAFF
        )

    def test_staff_cannot_update_organization(self):
        self.client.force_authenticate(self.staff)
        response = self.client.patch(
            f"/api/v1/organizations/{self.org.id}/", {"name": "Hacked"}
        )
        self.assertEqual(response.status_code, 403)

    def test_staff_cannot_delete_organization(self):
        self.client.force_authenticate(self.staff)
        response = self.client.delete(f"/api/v1/organizations/{self.org.id}/")
        self.assertEqual(response.status_code, 403)

    def test_owner_can_update_organization(self):
        self.client.force_authenticate(self.owner)
        response = self.client.patch(
            f"/api/v1/organizations/{self.org.id}/", {"name": "Salon A+"}
        )
        self.assertEqual(response.status_code, 200, response.data)

    def test_owner_can_delete_organization(self):
        self.client.force_authenticate(self.owner)
        response = self.client.delete(f"/api/v1/organizations/{self.org.id}/")
        self.assertEqual(response.status_code, 204)

    def test_creating_organization_grants_owner_role(self):
        self.client.force_authenticate(self.staff)
        response = self.client.post(
            "/api/v1/organizations/", {"name": "New Biz", "slug": "new-biz"}
        )
        self.assertEqual(response.status_code, 201, response.data)
        self.assertTrue(
            UserRole.objects.filter(
                user=self.staff,
                organization_id=response.data["id"],
                role=UserRole.Role.OWNER,
            ).exists()
        )


class UserSessionTests(APITestCase):
    """Login opens a session; rotation follows it; revocation kills it."""

    @classmethod
    def setUpTestData(cls):
        from django.contrib.auth import get_user_model

        cls.user = get_user_model().objects.create_user(
            email="sessions@namaa.sa", password="Str0ng!pass"
        )

    def _login(self):
        response = self.client.post(
            "/api/v1/auth/token/",
            {"email": "sessions@namaa.sa", "password": "Str0ng!pass"},
        )
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_login_opens_a_session(self):
        from accounts.models import UserSession

        self._login()
        session = UserSession.objects.get(user=self.user)
        self.assertIsNone(session.revoked_at)

    def test_refresh_rotation_keeps_the_same_session_row(self):
        from accounts.models import UserSession

        pair = self._login()
        refreshed = self.client.post(
            "/api/v1/auth/token/refresh/", {"refresh": pair["refresh"]}
        )
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(UserSession.objects.filter(user=self.user).count(), 1)

    def test_revoking_a_session_blacklists_its_refresh_token(self):
        from accounts.models import UserSession

        pair = self._login()
        session = UserSession.objects.get(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {pair['access']}")
        response = self.client.post(f"/api/v1/auth/sessions/{session.id}/revoke/")
        self.assertEqual(response.status_code, 200, response.data)
        # The revoked refresh token must no longer rotate.
        refreshed = self.client.post(
            "/api/v1/auth/token/refresh/", {"refresh": pair["refresh"]}
        )
        self.assertEqual(refreshed.status_code, 401)

    def test_users_only_see_their_own_sessions(self):
        from django.contrib.auth import get_user_model

        self._login()
        other = get_user_model().objects.create_user(
            email="other-sessions@namaa.sa", password="Str0ng!pass"
        )
        self.client.force_authenticate(other)
        response = self.client.get("/api/v1/auth/sessions/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)

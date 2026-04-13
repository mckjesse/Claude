"""
Auth flow tests: login, logout, me, and CSRF enforcement on /login/.
"""
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from apps.users.models import AppUser


class AuthFlowTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AppUser.objects.create_user(
            username="alice",
            password="testpass123",
            email="alice@test.local",
            display_name="Alice Test",
            role=AppUser.Role.ESTIMATOR,
        )

    # ---- me ----------------------------------------------------------
    def test_me_returns_401_when_unauthenticated(self):
        resp = self.client.get("/api/users/me/")
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        # Also serves as the CSRF bootstrap endpoint
        self.assertIn("csrftoken", resp.cookies)

    def test_me_returns_user_when_authenticated(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/users/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "alice")
        self.assertEqual(resp.data["role"], "estimator")
        self.assertEqual(resp.data["display_name"], "Alice Test")

    # ---- login -------------------------------------------------------
    def test_login_with_valid_credentials(self):
        resp = self.client.post(
            "/api/users/login/",
            {"username": "alice", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "alice")
        self.assertEqual(resp.data["role"], "estimator")
        # Session cookie is now set for subsequent calls on the same client
        self.assertIn("sessionid", resp.cookies)

    def test_login_rejects_wrong_password(self):
        resp = self.client.post(
            "/api/users/login/",
            {"username": "alice", "password": "wrong"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("sessionid", resp.cookies)

    def test_login_rejects_unknown_user(self):
        resp = self.client.post(
            "/api/users/login/",
            {"username": "nobody", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_login_requires_csrf_when_enforced(self):
        # The default DRF test client skips CSRF. Force it back on to
        # prove that the production login endpoint is CSRF-protected.
        client = APIClient(enforce_csrf_checks=True)
        resp = client.post(
            "/api/users/login/",
            {"username": "alice", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ---- logout ------------------------------------------------------
    def test_logout_ends_session(self):
        self.client.login(username="alice", password="testpass123")
        resp = self.client.post("/api/users/logout/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        follow = self.client.get("/api/users/me/")
        self.assertEqual(follow.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_logout_requires_authentication(self):
        resp = self.client.post("/api/users/logout/")
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

"""
Auth flow tests: JWT login, token refresh, /me/, logout.
"""
from rest_framework import status
from rest_framework.test import APITestCase

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

    # ---- /me/ --------------------------------------------------------
    def test_me_returns_401_when_unauthenticated(self):
        resp = self.client.get("/api/users/me/")
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_me_returns_user_when_authenticated(self):
        self.client.force_authenticate(user=self.user)
        resp = self.client.get("/api/users/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "alice")
        self.assertEqual(resp.data["role"], "estimator")
        self.assertEqual(resp.data["display_name"], "Alice Test")

    # ---- login -------------------------------------------------------
    def test_login_returns_jwt_tokens_and_user(self):
        resp = self.client.post(
            "/api/users/login/",
            {"username": "alice", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["username"], "alice")
        self.assertEqual(resp.data["user"]["role"], "estimator")
        self.assertEqual(resp.data["user"]["display_name"], "Alice Test")
        self.assertIn("id", resp.data["user"])

    def test_login_does_not_require_csrf(self):
        from rest_framework.test import APIClient

        client = APIClient(enforce_csrf_checks=True)
        resp = client.post(
            "/api/users/login/",
            {"username": "alice", "password": "testpass123"},
            format="json",
        )
        # JWT login is stateless — no CSRF needed even with enforcement on.
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_login_rejects_wrong_password(self):
        resp = self.client.post(
            "/api/users/login/",
            {"username": "alice", "password": "wrong"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn("access", resp.data)

    def test_login_rejects_unknown_user(self):
        resp = self.client.post(
            "/api/users/login/",
            {"username": "nobody", "password": "testpass123"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    # ---- JWT access --------------------------------------------------
    def test_jwt_access_token_authenticates_me(self):
        login = self.client.post(
            "/api/users/login/",
            {"username": "alice", "password": "testpass123"},
            format="json",
        )
        token = login.data["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        resp = self.client.get("/api/users/me/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["username"], "alice")

    # ---- token refresh -----------------------------------------------
    def test_refresh_returns_new_access_token(self):
        login = self.client.post(
            "/api/users/login/",
            {"username": "alice", "password": "testpass123"},
            format="json",
        )
        resp = self.client.post(
            "/api/users/token/refresh/",
            {"refresh": login.data["refresh"]},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("access", resp.data)

    # ---- logout (session cleanup, optional for JWT) ------------------
    def test_logout_requires_authentication(self):
        resp = self.client.post("/api/users/logout/")
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

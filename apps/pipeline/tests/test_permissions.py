"""
Role permission matrix tests.

One assertion per role per canonical action. Matches the role matrix
documented in apps/pipeline/permissions.py.
"""
from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, Opportunity
from apps.users.models import AppUser


class RolePermissionMatrixTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.company = Company.objects.create(
            name="PermCo", company_type=Company.Type.BUILDER,
        )
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.estimator = AppUser.objects.create_user(
            username="estimator", password="x", role=AppUser.Role.ESTIMATOR,
        )
        cls.pm = AppUser.objects.create_user(
            username="pm", password="x", role=AppUser.Role.PROJECT_MANAGER,
        )
        cls.admin = AppUser.objects.create_user(
            username="admin", password="x", role=AppUser.Role.ADMIN,
        )
        cls.readonly = AppUser.objects.create_user(
            username="readonly", password="x", role=AppUser.Role.READ_ONLY,
        )
        cls.opp = Opportunity.objects.create(
            project_name="Shared Opp",
            company=cls.company,
            estimator=cls.director,
        )

    def _as(self, user):
        self.client.force_authenticate(user=user)

    # ---- director -----------------------------------------------------
    def test_director_can_create_company(self):
        self._as(self.director)
        resp = self.client.post(
            "/api/companies/",
            {"name": "DirectorCo", "company_type": "builder"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_director_can_mark_won(self):
        self._as(self.director)
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "500000"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ---- estimator ----------------------------------------------------
    def test_estimator_cannot_create_company(self):
        self._as(self.estimator)
        resp = self.client.post(
            "/api/companies/",
            {"name": "Blocked", "company_type": "builder"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_estimator_can_create_quote(self):
        self._as(self.estimator)
        resp = self.client.post(
            "/api/quotes/",
            {"opportunity": self.opp.id, "revision_number": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_estimator_can_edit_opportunity_pricing(self):
        self._as(self.estimator)
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"estimated_contract_value": "1234000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    # ---- admin --------------------------------------------------------
    def test_admin_can_create_company(self):
        self._as(self.admin)
        resp = self.client.post(
            "/api/companies/",
            {"name": "AdminCo", "company_type": "builder"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_admin_can_edit_opportunity_metadata(self):
        self._as(self.admin)
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"notes": "admin touched this"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_admin_cannot_edit_opportunity_pricing(self):
        self._as(self.admin)
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"estimated_contract_value": "999999.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_change_stage(self):
        self._as(self.admin)
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.PRICING},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_create_quote(self):
        self._as(self.admin)
        resp = self.client.post(
            "/api/quotes/",
            {"opportunity": self.opp.id, "revision_number": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_cannot_mark_won(self):
        self._as(self.admin)
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "500000"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ---- project_manager ---------------------------------------------
    def test_project_manager_cannot_create_company(self):
        self._as(self.pm)
        resp = self.client.post(
            "/api/companies/",
            {"name": "PMCo", "company_type": "builder"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_project_manager_cannot_create_quote(self):
        self._as(self.pm)
        resp = self.client.post(
            "/api/quotes/",
            {"opportunity": self.opp.id, "revision_number": 1},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ---- read_only ----------------------------------------------------
    def test_read_only_cannot_create_company(self):
        self._as(self.readonly)
        resp = self.client.post(
            "/api/companies/",
            {"name": "ROCo", "company_type": "builder"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_only_cannot_patch_opportunity(self):
        self._as(self.readonly)
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"notes": "readonly edit"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_read_only_can_still_read(self):
        self._as(self.readonly)
        resp = self.client.get("/api/opportunities/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

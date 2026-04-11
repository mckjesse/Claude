"""
Opportunity creation + validation + mark_won / mark_lost.
"""
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, LossReason, Opportunity
from apps.users.models import AppUser


class OpportunityCreationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="Test Builder", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)

    def test_create_opportunity_succeeds(self):
        resp = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "Test Project",
                "project_code": "TEST-001",
                "company": self.company.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["project_name"], "Test Project")
        # Default stage is lead and status is open
        self.assertEqual(resp.data["stage"], Opportunity.Stage.LEAD)
        self.assertEqual(resp.data["status"], Opportunity.Status.OPEN)

    def test_create_opportunity_requires_company(self):
        resp = self.client.post(
            "/api/opportunities/",
            {"project_name": "No Company"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company", resp.data)


class OpportunityValidationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="Validator Co", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="Validation Target",
            company=self.company,
            estimator=self.director,
        )

    def test_stage_won_requires_final_awarded_value(self):
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.WON},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("final_awarded_value", resp.data)

    def test_probability_percent_must_be_0_to_100(self):
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"probability_percent": 150},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("probability_percent", resp.data)


class MarkWonTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="MarkWonCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="WinTarget",
            company=self.company,
            estimator=self.director,
        )

    def test_mark_won_requires_final_awarded_value(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("final_awarded_value", resp.data)

    def test_mark_won_rejects_negative_value(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "-500"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_won_sets_stage_status_and_value(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "500000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.WON)
        self.assertEqual(self.opp.status, Opportunity.Status.CLOSED)
        self.assertEqual(self.opp.final_awarded_value, Decimal("500000.00"))


class MarkLostTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="MarkLostCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="LossTarget",
            company=self.company,
            estimator=self.director,
        )

    def test_mark_lost_requires_reason_category(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason_category", resp.data)

    def test_mark_lost_rejects_invalid_reason_category(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {"reason_category": "not-a-real-category"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_lost_creates_loss_reason_and_closes_opportunity(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {
                "reason_category": LossReason.Category.PRICE,
                "competitor_name": "BigBuild Co",
                "reason_detail": "Client went cheaper.",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.LOST)
        self.assertEqual(self.opp.status, Opportunity.Status.CLOSED)

        lr = LossReason.objects.get(opportunity=self.opp)
        self.assertEqual(lr.reason_category, LossReason.Category.PRICE)
        self.assertEqual(lr.competitor_name, "BigBuild Co")

    def test_mark_lost_is_idempotent(self):
        # First call creates the LossReason
        self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {"reason_category": LossReason.Category.PRICE},
            format="json",
        )
        # Second call updates the same row, does not create a duplicate
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {
                "reason_category": LossReason.Category.SCOPE,
                "competitor_name": "Updated Rival",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            LossReason.objects.filter(opportunity=self.opp).count(), 1
        )
        lr = LossReason.objects.get(opportunity=self.opp)
        self.assertEqual(lr.reason_category, LossReason.Category.SCOPE)
        self.assertEqual(lr.competitor_name, "Updated Rival")

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

    def test_create_opportunity_requires_project_code(self):
        # project_code is the Project ID — the canonical human identifier.
        resp = self.client.post(
            "/api/opportunities/",
            {"project_name": "No ID", "company": self.company.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_code", resp.data)

    def test_project_code_must_be_unique(self):
        self.client.post(
            "/api/opportunities/",
            {
                "project_name": "First",
                "project_code": "UNIQ-1",
                "company": self.company.id,
            },
            format="json",
        )
        resp = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "Dupe",
                "project_code": "UNIQ-1",
                "company": self.company.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_code", resp.data)


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
            project_code="VAL-001",
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
            project_code="WIN-001",
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

    def test_direct_patch_to_won_auto_closes_status(self):
        # PATCH stage=won with final_awarded_value should still force
        # status=closed, even though this path bypasses mark_won.
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.WON, "final_awarded_value": "123000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.WON)
        self.assertEqual(self.opp.status, Opportunity.Status.CLOSED)


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
            project_code="LOSS-001",
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

    def test_direct_patch_to_lost_is_rejected_without_existing_reason(self):
        # Direct PATCH must not be able to set stage=lost without a
        # LossReason being recorded. Callers are forced through
        # POST /mark_lost/.
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.LOST},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stage", resp.data)
        self.opp.refresh_from_db()
        # State is unchanged
        self.assertNotEqual(self.opp.stage, Opportunity.Stage.LOST)

    def test_direct_patch_to_lost_works_when_reason_already_exists(self):
        # Having already marked lost via the canonical action, a
        # follow-up PATCH that re-states stage=lost is harmless.
        self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {"reason_category": LossReason.Category.PRICE},
            format="json",
        )
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.LOST, "notes": "post-loss note"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.LOST)
        self.assertEqual(self.opp.status, Opportunity.Status.CLOSED)

    def test_direct_patch_out_of_lost_is_blocked(self):
        # Trying to PATCH stage away from 'lost' must be rejected.
        self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {"reason_category": LossReason.Category.PRICE},
            format="json",
        )
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.LEAD},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stage", resp.data)


class ReopenTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="reopen_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="ReopenCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="ReopenTarget",
            project_code=f"RE-{self.id()[-6:]}",
            company=self.company,
            estimator=self.director,
            stage=Opportunity.Stage.LOST,
            status=Opportunity.Status.CLOSED,
        )
        LossReason.objects.create(
            opportunity=self.opp,
            reason_category=LossReason.Category.PRICE,
            reason_detail="Original loss.",
        )

    def test_reopen_sets_stage_follow_up_and_status_open(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.FOLLOW_UP)
        self.assertEqual(self.opp.status, Opportunity.Status.OPEN)

    def test_reopen_preserves_loss_reason(self):
        self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        lr = LossReason.objects.get(opportunity=self.opp)
        self.assertEqual(lr.reason_category, LossReason.Category.PRICE)
        self.assertEqual(lr.reason_detail, "Original loss.")

    def test_reopen_creates_activity_entries(self):
        from apps.pipeline.models import ActivityLog

        before = ActivityLog.objects.filter(opportunity=self.opp).count()
        self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        after = ActivityLog.objects.filter(opportunity=self.opp).count()
        self.assertEqual(after - before, 2)  # stage_changed + reopened

    def test_reopen_rejects_non_terminal_opportunity(self):
        self.opp.stage = Opportunity.Stage.PRICING
        self.opp.status = Opportunity.Status.OPEN
        self.opp.save()
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reopen_works_on_won_opportunity(self):
        self.opp.stage = Opportunity.Stage.WON
        self.opp.final_awarded_value = "500000.00"
        self.opp.save()
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.FOLLOW_UP)
        self.assertEqual(self.opp.status, Opportunity.Status.OPEN)

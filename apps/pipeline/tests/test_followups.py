"""
Follow-up behaviour tests:
- completion auto-stamps completed_at
- is_overdue computed field
- estimator relevance rule on create
"""
from datetime import date, timedelta

from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, FollowUpTask, Opportunity
from apps.users.models import AppUser


class FollowUpCompletionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="FUCo", company_type=Company.Type.BUILDER,
        )
        cls.opp = Opportunity.objects.create(
            project_name="FUOpp",
            project_code="FU-001",
            company=cls.company,
            estimator=cls.director,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)

    def test_completion_auto_stamps_completed_at(self):
        task = FollowUpTask.objects.create(
            opportunity=self.opp,
            assigned_to_user=self.director,
            task_type=FollowUpTask.TaskType.CALL,
            subject="Call client",
            due_date=date.today(),
        )
        self.assertIsNone(task.completed_at)

        resp = self.client.patch(
            f"/api/followups/{task.id}/",
            {"status": FollowUpTask.Status.COMPLETED},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        task.refresh_from_db()
        self.assertEqual(task.status, FollowUpTask.Status.COMPLETED)
        self.assertIsNotNone(task.completed_at)

    def test_is_overdue_true_for_past_pending(self):
        task = FollowUpTask.objects.create(
            opportunity=self.opp,
            assigned_to_user=self.director,
            task_type=FollowUpTask.TaskType.CALL,
            subject="Old pending",
            due_date=date.today() - timedelta(days=3),
            status=FollowUpTask.Status.PENDING,
        )
        resp = self.client.get(f"/api/followups/{task.id}/")
        self.assertTrue(resp.data["is_overdue"])

    def test_is_overdue_false_for_completed_task(self):
        task = FollowUpTask.objects.create(
            opportunity=self.opp,
            assigned_to_user=self.director,
            task_type=FollowUpTask.TaskType.CALL,
            subject="Old done",
            due_date=date.today() - timedelta(days=3),
            status=FollowUpTask.Status.COMPLETED,
        )
        resp = self.client.get(f"/api/followups/{task.id}/")
        self.assertFalse(resp.data["is_overdue"])

    def test_is_overdue_false_for_future_task(self):
        task = FollowUpTask.objects.create(
            opportunity=self.opp,
            assigned_to_user=self.director,
            task_type=FollowUpTask.TaskType.CALL,
            subject="Future",
            due_date=date.today() + timedelta(days=3),
            status=FollowUpTask.Status.PENDING,
        )
        resp = self.client.get(f"/api/followups/{task.id}/")
        self.assertFalse(resp.data["is_overdue"])


class FollowUpEstimatorRelevanceTests(APITestCase):
    """Estimators may only create follow-ups on relevant opportunities."""

    @classmethod
    def setUpTestData(cls):
        cls.eli = AppUser.objects.create_user(
            username="eli", password="x", role=AppUser.Role.ESTIMATOR,
        )
        cls.frank = AppUser.objects.create_user(
            username="frank", password="x", role=AppUser.Role.ESTIMATOR,
        )
        cls.company = Company.objects.create(
            name="RelCo", company_type=Company.Type.BUILDER,
        )
        # Relevant for Eli — Eli is the estimator.
        cls.relevant_opp = Opportunity.objects.create(
            project_name="Eli Opp",
            project_code="REL-ELI",
            company=cls.company,
            estimator=cls.eli,
            assigned_user=cls.eli,
        )
        # Relevant for Frank only — Eli is neither estimator nor assigned.
        cls.irrelevant_opp = Opportunity.objects.create(
            project_name="Frank Opp",
            project_code="REL-FRANK",
            company=cls.company,
            estimator=cls.frank,
            assigned_user=cls.frank,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.eli)

    def test_estimator_can_create_followup_on_relevant_opp(self):
        resp = self.client.post(
            "/api/followups/",
            {
                "opportunity": self.relevant_opp.id,
                "assigned_to_user": self.eli.id,
                "subject": "Relevant task",
                "task_type": FollowUpTask.TaskType.CALL,
                "due_date": "2099-01-01",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

    def test_estimator_cannot_create_followup_on_irrelevant_opp(self):
        resp = self.client.post(
            "/api/followups/",
            {
                "opportunity": self.irrelevant_opp.id,
                "assigned_to_user": self.eli.id,
                "subject": "Blocked task",
                "task_type": FollowUpTask.TaskType.CALL,
                "due_date": "2099-01-01",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

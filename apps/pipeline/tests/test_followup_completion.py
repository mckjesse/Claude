"""
Follow-up completion workflow: complete with notes, successor creation,
reopen.
"""
from datetime import date, timedelta

from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, FollowUpTask, Opportunity
from apps.users.models import AppUser


class FollowUpCompleteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="cmp_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="CmpCo", company_type=Company.Type.BUILDER,
        )
        cls.opp = Opportunity.objects.create(
            project_name="CmpOpp",
            project_code="CMP-001",
            company=cls.company,
            estimator=cls.director,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.task = FollowUpTask.objects.create(
            opportunity=self.opp,
            assigned_to_user=self.director,
            subject="Original task",
            task_type=FollowUpTask.TaskType.CALL,
            priority=FollowUpTask.Priority.HIGH,
            status=FollowUpTask.Status.PENDING,
            due_date=date.today(),
        )

    # ---- complete action ---------------------------------------------
    def test_complete_requires_notes(self):
        resp = self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("completion_notes", resp.data)

    def test_complete_sets_all_fields(self):
        resp = self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {"completion_notes": "Called builder; waiting on feedback"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, FollowUpTask.Status.COMPLETED)
        self.assertIsNotNone(self.task.completed_at)
        self.assertEqual(self.task.completed_by, self.director)
        self.assertEqual(
            self.task.completion_notes,
            "Called builder; waiting on feedback",
        )

    def test_complete_creates_successor_followup(self):
        self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {"completion_notes": "Done"},
            format="json",
        )
        successors = FollowUpTask.objects.filter(
            opportunity=self.opp,
            subject="Follow up again",
        )
        self.assertEqual(successors.count(), 1)
        s = successors.first()
        self.assertEqual(s.task_type, FollowUpTask.TaskType.CALL)
        self.assertEqual(s.priority, FollowUpTask.Priority.HIGH)
        self.assertEqual(s.status, FollowUpTask.Status.PENDING)
        self.assertEqual(
            s.due_date, self.task.due_date + timedelta(days=14)
        )
        self.assertEqual(s.assigned_to_user, self.director)

    def test_complete_is_idempotent(self):
        self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {"completion_notes": "Done"},
            format="json",
        )
        resp = self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {"completion_notes": "Again"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_no_duplicate_successor_on_retry(self):
        self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {"completion_notes": "First"},
            format="json",
        )
        # Complete the successor too — should not create another with
        # the same subject while one is already pending.
        second = FollowUpTask.objects.create(
            opportunity=self.opp,
            assigned_to_user=self.director,
            subject="Another task",
            task_type=FollowUpTask.TaskType.EMAIL,
            priority=FollowUpTask.Priority.MEDIUM,
            status=FollowUpTask.Status.PENDING,
            due_date=date.today(),
        )
        self.client.post(
            f"/api/followups/{second.id}/complete/",
            {"completion_notes": "Second"},
            format="json",
        )
        follow_up_again = FollowUpTask.objects.filter(
            opportunity=self.opp, subject="Follow up again"
        )
        # Only one "Follow up again" because the first one still exists
        # and is pending.
        self.assertEqual(follow_up_again.count(), 1)


class FollowUpReopenTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="reop_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="ReopCo", company_type=Company.Type.BUILDER,
        )
        cls.opp = Opportunity.objects.create(
            project_name="ReopOpp",
            project_code="REOP-001",
            company=cls.company,
            estimator=cls.director,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.task = FollowUpTask.objects.create(
            opportunity=self.opp,
            assigned_to_user=self.director,
            subject="Reopen test",
            task_type=FollowUpTask.TaskType.CALL,
            priority=FollowUpTask.Priority.HIGH,
            status=FollowUpTask.Status.COMPLETED,
            due_date=date.today(),
            completion_notes="Was done, now not.",
        )

    def test_reopen_sets_pending_and_clears_timestamps(self):
        resp = self.client.post(
            f"/api/followups/{self.task.id}/reopen/", format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, FollowUpTask.Status.PENDING)
        self.assertIsNone(self.task.completed_at)
        self.assertIsNone(self.task.completed_by)

    def test_reopen_preserves_completion_notes(self):
        self.client.post(
            f"/api/followups/{self.task.id}/reopen/", format="json"
        )
        self.task.refresh_from_db()
        self.assertEqual(self.task.completion_notes, "Was done, now not.")

    def test_reopen_rejects_non_completed_task(self):
        self.task.status = FollowUpTask.Status.PENDING
        self.task.save()
        resp = self.client.post(
            f"/api/followups/{self.task.id}/reopen/", format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reopen_creates_activity_log(self):
        from apps.pipeline.models import ActivityLog

        before = ActivityLog.objects.filter(opportunity=self.opp).count()
        self.client.post(
            f"/api/followups/{self.task.id}/reopen/", format="json"
        )
        after = ActivityLog.objects.filter(opportunity=self.opp).count()
        self.assertGreater(after, before)

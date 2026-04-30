"""
Follow-up completion workflow: close-out vs schedule-next, reopen.
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

    # ---- validation --------------------------------------------------
    def test_complete_requires_notes(self):
        resp = self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("completion_notes", resp.data)

    def test_complete_rejects_already_completed(self):
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

    # ---- close-out (schedule_next = false / omitted) -----------------
    def test_close_out_completes_without_successor(self):
        resp = self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {"completion_notes": "Called builder; done."},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, FollowUpTask.Status.COMPLETED)
        self.assertIsNotNone(self.task.completed_at)
        self.assertEqual(self.task.completed_by, self.director)
        self.assertEqual(self.task.completion_notes, "Called builder; done.")
        # No successor created.
        self.assertNotIn("next_followup", resp.data)
        successors = FollowUpTask.objects.filter(
            opportunity=self.opp, subject="Follow up again"
        )
        self.assertEqual(successors.count(), 0)

    # ---- schedule-next -----------------------------------------------
    def test_schedule_next_creates_successor_with_defaults(self):
        resp = self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {"completion_notes": "Needs more chasing", "schedule_next": True},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("next_followup", resp.data)
        nf = resp.data["next_followup"]
        self.assertEqual(nf["subject"], "Follow up again")
        self.assertEqual(nf["task_type"], FollowUpTask.TaskType.CALL)
        self.assertEqual(nf["priority"], FollowUpTask.Priority.HIGH)
        expected_due = str(self.task.due_date + timedelta(days=14))
        self.assertEqual(nf["due_date"], expected_due)

    def test_schedule_next_uses_custom_fields(self):
        resp = self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {
                "completion_notes": "Switch to email",
                "schedule_next": True,
                "next_due_date": "2026-07-01",
                "next_subject": "Custom subject",
                "next_task_type": "email",
                "next_priority": "low",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        nf = resp.data["next_followup"]
        self.assertEqual(nf["due_date"], "2026-07-01")
        self.assertEqual(nf["subject"], "Custom subject")
        self.assertEqual(nf["task_type"], "email")
        self.assertEqual(nf["priority"], "low")

    def test_schedule_next_bad_date_is_rejected(self):
        resp = self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {
                "completion_notes": "Bad date",
                "schedule_next": True,
                "next_due_date": "not-a-date",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("next_due_date", resp.data)

    def test_no_duplicate_successor(self):
        self.client.post(
            f"/api/followups/{self.task.id}/complete/",
            {"completion_notes": "First", "schedule_next": True},
            format="json",
        )
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
            {"completion_notes": "Second", "schedule_next": True},
            format="json",
        )
        follow_up_again = FollowUpTask.objects.filter(
            opportunity=self.opp, subject="Follow up again"
        )
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

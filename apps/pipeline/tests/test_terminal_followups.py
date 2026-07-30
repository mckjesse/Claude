"""
Terminal (won/lost/closed) opportunity behaviour:

  - marking an opportunity won or lost cancels its outstanding
    follow-ups (never hard-deletes them),
  - completed historical follow-ups are left untouched,
  - terminal opportunities disappear from the stale list, and
  - their follow-ups disappear from the dashboard's pending list.
"""
from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, FollowUpTask, LossReason, Opportunity
from apps.pipeline.services import dashboard, reports
from apps.users.models import AppUser


class TerminalFollowupClearingTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="term_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.other = AppUser.objects.create_user(
            username="term_other", password="x", role=AppUser.Role.ESTIMATOR,
        )
        cls.company = Company.objects.create(
            name="TerminalCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="TerminalTarget",
            project_code="TERM-001",
            company=self.company,
            estimator=self.director,
            stage=Opportunity.Stage.SUBMITTED,
        )

    def _make_followup(self, *, subject, status=FollowUpTask.Status.PENDING,
                       due_offset=-3, completed_at=None, completed_by=None,
                       completion_notes="", opportunity=None):
        return FollowUpTask.objects.create(
            opportunity=opportunity or self.opp,
            assigned_to_user=self.director,
            subject=subject,
            task_type=FollowUpTask.TaskType.CALL,
            priority=FollowUpTask.Priority.HIGH,
            status=status,
            due_date=timezone.localdate() + timedelta(days=due_offset),
            completed_at=completed_at,
            completed_by=completed_by,
            completion_notes=completion_notes,
        )

    # --- clearing on won ----------------------------------------------
    def test_mark_won_clears_pending_followups(self):
        t1 = self._make_followup(subject="Chase 1")
        t2 = self._make_followup(subject="Chase 2")

        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "250000"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Response payload (requirement 5).
        self.assertEqual(resp.data["cleared_followups_count"], 2)
        self.assertCountEqual(resp.data["cleared_followup_ids"], [t1.id, t2.id])
        self.assertEqual(
            resp.data["opportunity"]["stage"], Opportunity.Stage.WON
        )

        for t in (t1, t2):
            t.refresh_from_db()
            self.assertEqual(t.status, FollowUpTask.Status.CANCELLED)
            self.assertIsNotNone(t.completed_at)
            self.assertEqual(t.completed_by, self.director)
            self.assertIn("marked as won", t.completion_notes)

    # --- clearing on lost ---------------------------------------------
    def test_mark_lost_clears_pending_followups(self):
        t1 = self._make_followup(subject="Chase A")

        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {"reason_category": LossReason.Category.PRICE},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["cleared_followups_count"], 1)
        self.assertEqual(resp.data["cleared_followup_ids"], [t1.id])

        t1.refresh_from_db()
        self.assertEqual(t1.status, FollowUpTask.Status.CANCELLED)
        self.assertIn("marked as lost", t1.completion_notes)

    # --- historical completed follow-ups are untouched ----------------
    def test_completed_historical_followups_unchanged(self):
        done = self._make_followup(
            subject="Already done",
            status=FollowUpTask.Status.COMPLETED,
            completed_at=timezone.now() - timedelta(days=5),
            completed_by=self.other,
            completion_notes="Handled earlier.",
        )
        pending = self._make_followup(subject="Still open")

        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "250000"},
            format="json",
        )
        self.assertEqual(resp.data["cleared_followup_ids"], [pending.id])

        done.refresh_from_db()
        self.assertEqual(done.status, FollowUpTask.Status.COMPLETED)
        self.assertEqual(done.completed_by, self.other)
        self.assertEqual(done.completion_notes, "Handled earlier.")

    # --- follow-ups are cancelled, never deleted ----------------------
    def test_followups_are_not_hard_deleted(self):
        t1 = self._make_followup(subject="Keep the row")
        self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "250000"},
            format="json",
        )
        self.assertTrue(FollowUpTask.objects.filter(id=t1.id).exists())

    # --- PATCH to a terminal stage also clears ------------------------
    def test_patch_to_won_clears_pending_followups(self):
        t1 = self._make_followup(subject="Chase via patch")
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.WON, "final_awarded_value": "123000"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        t1.refresh_from_db()
        self.assertEqual(t1.status, FollowUpTask.Status.CANCELLED)


class TerminalDashboardAndStaleTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="term_dash_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="TermDashCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)

    def _stale_opp(self, code):
        return Opportunity.objects.create(
            project_name=f"Stale {code}",
            project_code=code,
            company=self.company,
            estimator=self.director,
            stage=Opportunity.Stage.SUBMITTED,
            submission_date=timezone.localdate() - timedelta(days=45),
        )

    def _overdue_followup(self, opp):
        return FollowUpTask.objects.create(
            opportunity=opp,
            assigned_to_user=self.director,
            subject="Overdue chase",
            task_type=FollowUpTask.TaskType.CALL,
            status=FollowUpTask.Status.PENDING,
            due_date=timezone.localdate() - timedelta(days=3),
        )

    def _stale_ids(self):
        return {r["id"] for r in reports.stale_opportunities(self.director)}

    def _dashboard_followup_ids(self):
        d = dashboard.build_dashboard(self.director)
        return {t["id"] for t in d["top_overdue_followups"]}

    # --- stale exclusion ----------------------------------------------
    def test_won_opportunity_never_in_stale_list(self):
        opp = self._stale_opp("STALE-WON")
        self.assertIn(opp.id, self._stale_ids())
        self.client.post(
            f"/api/opportunities/{opp.id}/mark_won/",
            {"final_awarded_value": "250000"},
            format="json",
        )
        self.assertNotIn(opp.id, self._stale_ids())

    def test_lost_opportunity_never_in_stale_list(self):
        opp = self._stale_opp("STALE-LOST")
        self.assertIn(opp.id, self._stale_ids())
        self.client.post(
            f"/api/opportunities/{opp.id}/mark_lost/",
            {"reason_category": LossReason.Category.PRICE},
            format="json",
        )
        self.assertNotIn(opp.id, self._stale_ids())

    # --- dashboard pending follow-up exclusion ------------------------
    def test_cancelled_followup_no_longer_on_dashboard(self):
        opp = self._stale_opp("DASH-WON")
        task = self._overdue_followup(opp)
        # Visible while still pending.
        self.assertIn(task.id, self._dashboard_followup_ids())

        self.client.post(
            f"/api/opportunities/{opp.id}/mark_won/",
            {"final_awarded_value": "250000"},
            format="json",
        )
        task.refresh_from_db()
        self.assertEqual(task.status, FollowUpTask.Status.CANCELLED)
        self.assertNotIn(task.id, self._dashboard_followup_ids())

    def test_followup_on_terminal_opp_excluded_even_if_still_pending(self):
        # Belt-and-suspenders: a stray PENDING follow-up under a terminal
        # opportunity must not surface on the dashboard, regardless of the
        # auto-cancel step (requirement 4, parent-opportunity filter).
        opp = Opportunity.objects.create(
            project_name="Already Won",
            project_code="DASH-TERMINAL",
            company=self.company,
            estimator=self.director,
            stage=Opportunity.Stage.WON,
            status=Opportunity.Status.CLOSED,
        )
        task = self._overdue_followup(opp)  # created directly as PENDING
        self.assertNotIn(task.id, self._dashboard_followup_ids())

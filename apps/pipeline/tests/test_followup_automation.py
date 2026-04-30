"""
Automatic follow-up creation when opportunity stage → submitted.
"""
from datetime import date, timedelta
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, FollowUpTask, Opportunity
from apps.users.models import AppUser


class FollowUpAutomationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="fu_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.estimator = AppUser.objects.create_user(
            username="fu_est", password="x", role=AppUser.Role.ESTIMATOR,
        )
        cls.company = Company.objects.create(
            name="FUAutoCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)

    def _create_opp(self, code, **extra):
        data = {
            "project_name": f"FU {code}",
            "project_code": code,
            "company": self.company.id,
            "stage": Opportunity.Stage.LEAD,
            "estimated_contract_value": "500000.00",
            **extra,
        }
        resp = self.client.post("/api/opportunities/", data, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        return resp.data["id"]

    def _tasks(self, opp_id):
        return FollowUpTask.objects.filter(opportunity_id=opp_id)

    # ---- triggers correctly ------------------------------------------
    def test_followup_created_on_transition_to_submitted(self):
        opp_id = self._create_opp("FUA-01")
        self.assertEqual(self._tasks(opp_id).count(), 0)
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        tasks = self._tasks(opp_id)
        self.assertEqual(tasks.count(), 1)
        t = tasks.first()
        self.assertEqual(t.subject, "Follow up on submitted quote")
        self.assertEqual(t.task_type, FollowUpTask.TaskType.EMAIL)
        self.assertEqual(t.status, FollowUpTask.Status.PENDING)
        self.assertEqual(t.priority, FollowUpTask.Priority.MEDIUM)

    def test_followup_created_on_create_at_submitted(self):
        opp_id = self._create_opp("FUA-02", stage=Opportunity.Stage.SUBMITTED)
        self.assertEqual(self._tasks(opp_id).count(), 1)

    # ---- due date ----------------------------------------------------
    def test_due_date_is_submission_date_plus_14(self):
        opp_id = self._create_opp(
            "FUA-03", submission_date="2026-06-01"
        )
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        t = self._tasks(opp_id).first()
        self.assertEqual(t.due_date, date(2026, 6, 15))

    def test_due_date_falls_back_to_today_plus_14(self):
        opp_id = self._create_opp("FUA-04")
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        t = self._tasks(opp_id).first()
        expected = date.today() + timedelta(days=14)
        self.assertEqual(t.due_date, expected)

    # ---- assignment --------------------------------------------------
    def test_assigned_to_assigned_user(self):
        opp_id = self._create_opp(
            "FUA-05", assigned_user=self.estimator.id,
        )
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        t = self._tasks(opp_id).first()
        self.assertEqual(t.assigned_to_user_id, self.estimator.id)

    def test_falls_back_to_estimator(self):
        opp_id = self._create_opp(
            "FUA-06", estimator=self.estimator.id,
        )
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        t = self._tasks(opp_id).first()
        self.assertEqual(t.assigned_to_user_id, self.estimator.id)

    # ---- duplicate prevention ----------------------------------------
    def test_no_duplicate_on_repeat_transition(self):
        opp_id = self._create_opp("FUA-07")
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        self.assertEqual(self._tasks(opp_id).count(), 1)
        # Move away then back to submitted.
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.FOLLOW_UP},
            format="json",
        )
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        self.assertEqual(self._tasks(opp_id).count(), 1)

    def test_no_duplicate_on_unrelated_edit(self):
        opp_id = self._create_opp(
            "FUA-08", stage=Opportunity.Stage.SUBMITTED,
        )
        self.assertEqual(self._tasks(opp_id).count(), 1)
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"notes": "just a note"},
            format="json",
        )
        self.assertEqual(self._tasks(opp_id).count(), 1)

    # ---- no-op for other stages --------------------------------------
    def test_no_followup_for_pricing_stage(self):
        opp_id = self._create_opp("FUA-09")
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.PRICING},
            format="json",
        )
        self.assertEqual(self._tasks(opp_id).count(), 0)

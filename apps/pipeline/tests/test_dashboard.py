"""
Dashboard endpoint tests:
- requires authentication
- returns the expected top-level shape
- row-level visibility: project manager sees only won-scoped data
"""
from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, FollowUpTask, Opportunity
from apps.users.models import AppUser


class DashboardAuthAndShapeTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="DashCo", company_type=Company.Type.BUILDER,
        )
        Opportunity.objects.create(
            project_name="Open 1",
            project_code="DSH-001",
            company=cls.company,
            estimator=cls.director,
            estimated_contract_value=Decimal("1000000.00"),
            stage=Opportunity.Stage.PRICING,
        )
        Opportunity.objects.create(
            project_name="Open 2",
            project_code="DSH-002",
            company=cls.company,
            estimator=cls.director,
            estimated_contract_value=Decimal("500000.00"),
            stage=Opportunity.Stage.INVITED,
        )

    def test_dashboard_requires_authentication(self):
        resp = self.client.get("/api/dashboard/")
        self.assertIn(
            resp.status_code,
            (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN),
        )

    def test_dashboard_returns_expected_shape(self):
        self.client.force_authenticate(user=self.director)
        resp = self.client.get("/api/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

        expected_keys = {
            "total_open_pipeline_value",
            "active_opportunities",
            "quotes_awaiting_follow_up",
            "overdue_followups",
            "followups_due_today",
            "upcoming_submissions_7_days",
            "opportunities_by_stage",
            "recent_activity",
            "top_overdue_followups",
        }
        self.assertEqual(set(resp.data.keys()), expected_keys)

        self.assertEqual(resp.data["active_opportunities"], 2)
        # Two open opportunities totalling 1.5M
        self.assertEqual(
            Decimal(resp.data["total_open_pipeline_value"]),
            Decimal("1500000.00"),
        )
        # Stage breakdown is always zero-filled for all 9 stages
        self.assertEqual(len(resp.data["opportunities_by_stage"]), 9)


class DashboardRowLevelVisibilityTests(APITestCase):
    """
    Project managers only see opportunities with stage=won. Everything
    else — dashboard counts, stage breakdown, recent activity — should
    respect that same scope.
    """

    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.pm = AppUser.objects.create_user(
            username="pm", password="x", role=AppUser.Role.PROJECT_MANAGER,
        )
        cls.company = Company.objects.create(
            name="VisCo", company_type=Company.Type.BUILDER,
        )

        Opportunity.objects.create(
            project_name="Live pricing",
            project_code="VIS-001",
            company=cls.company,
            estimator=cls.director,
            estimated_contract_value=Decimal("750000.00"),
            stage=Opportunity.Stage.PRICING,
        )
        Opportunity.objects.create(
            project_name="Live submitted",
            project_code="VIS-002",
            company=cls.company,
            estimator=cls.director,
            estimated_contract_value=Decimal("900000.00"),
            stage=Opportunity.Stage.SUBMITTED,
        )
        Opportunity.objects.create(
            project_name="Won deal",
            project_code="VIS-003",
            company=cls.company,
            estimator=cls.director,
            estimated_contract_value=Decimal("600000.00"),
            final_awarded_value=Decimal("580000.00"),
            stage=Opportunity.Stage.WON,
            status=Opportunity.Status.CLOSED,
        )
        Opportunity.objects.create(
            project_name="Lost deal",
            project_code="VIS-004",
            company=cls.company,
            estimator=cls.director,
            estimated_contract_value=Decimal("400000.00"),
            stage=Opportunity.Stage.LOST,
            status=Opportunity.Status.CLOSED,
        )

    def test_director_sees_all_opportunities_in_list(self):
        self.client.force_authenticate(user=self.director)
        resp = self.client.get("/api/opportunities/")
        self.assertEqual(resp.data["count"], 4)

    def test_project_manager_sees_only_won_in_list(self):
        self.client.force_authenticate(user=self.pm)
        resp = self.client.get("/api/opportunities/")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(
            resp.data["results"][0]["project_name"], "Won deal"
        )

    def test_dashboard_active_count_for_director(self):
        self.client.force_authenticate(user=self.director)
        resp = self.client.get("/api/dashboard/")
        # Open opps: 2 (pricing + submitted). Won and Lost are both closed.
        self.assertEqual(resp.data["active_opportunities"], 2)

    def test_dashboard_active_count_for_project_manager(self):
        self.client.force_authenticate(user=self.pm)
        resp = self.client.get("/api/dashboard/")
        # PM only sees won opps — which are all closed, so zero active.
        self.assertEqual(resp.data["active_opportunities"], 0)

    def test_project_manager_company_list_is_scoped(self):
        # PM sees only companies that have at least one won opp.
        # We only have one company with a won opp, so count == 1.
        self.client.force_authenticate(user=self.pm)
        resp = self.client.get("/api/companies/")
        self.assertEqual(resp.data["count"], 1)


class TopOverdueFollowupOrderingTests(APITestCase):
    """
    ``priority`` is a CharField, so ordering by ``-priority`` sorts
    alphabetically (medium, low, high, critical) and buries the most
    urgent tasks. The dashboard must rank the values explicitly.
    """

    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="prio_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="PrioCo", company_type=Company.Type.BUILDER,
        )
        cls.opp = Opportunity.objects.create(
            project_name="Prio Project",
            project_code="PRIO-001",
            company=cls.company,
            estimator=cls.director,
            stage=Opportunity.Stage.FOLLOW_UP,
        )
        overdue_on = timezone.localdate() - timedelta(days=5)
        # Created in a deliberately unhelpful order so a stable sort
        # cannot accidentally produce the right answer.
        for priority in (
            FollowUpTask.Priority.LOW,
            FollowUpTask.Priority.CRITICAL,
            FollowUpTask.Priority.MEDIUM,
            FollowUpTask.Priority.HIGH,
        ):
            FollowUpTask.objects.create(
                opportunity=cls.opp,
                assigned_to_user=cls.director,
                subject=f"Chase ({priority})",
                task_type=FollowUpTask.TaskType.CALL,
                due_date=overdue_on,
                priority=priority,
                status=FollowUpTask.Status.PENDING,
            )

    def test_top_overdue_followups_are_ordered_most_urgent_first(self):
        self.client.force_authenticate(user=self.director)
        resp = self.client.get("/api/dashboard/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [t["priority"] for t in resp.data["top_overdue_followups"]],
            ["critical", "high", "medium", "low"],
        )

    def test_due_date_still_takes_precedence_over_priority(self):
        # An older low-priority task outranks a newer critical one:
        # due_date is the primary sort key, priority only breaks ties.
        FollowUpTask.objects.create(
            opportunity=self.opp,
            assigned_to_user=self.director,
            subject="Oldest, lowest priority",
            task_type=FollowUpTask.TaskType.CALL,
            due_date=timezone.localdate() - timedelta(days=30),
            priority=FollowUpTask.Priority.LOW,
            status=FollowUpTask.Status.PENDING,
        )
        self.client.force_authenticate(user=self.director)
        resp = self.client.get("/api/dashboard/")
        first = resp.data["top_overdue_followups"][0]
        self.assertEqual(first["subject"], "Oldest, lowest priority")

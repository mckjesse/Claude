"""
Stale opportunity report rules.

An opportunity is stale only when:
  - not archived
  - stage in {submitted, follow_up, negotiating}
  - >= 30 days since effective submission date
  - no pending/in-progress follow-up with due_date >= today
"""
from datetime import date, timedelta
from decimal import Decimal

from django.utils import timezone
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, FollowUpTask, Opportunity
from apps.pipeline.services import reports
from apps.users.models import AppUser


class StaleOpportunityTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = AppUser.objects.create_user(
            username="stale_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="StaleCo", company_type=Company.Type.BUILDER,
        )

    def _make_opp(self, code, *, stage, submission_offset_days, status=None):
        today = timezone.localdate()
        return Opportunity.objects.create(
            project_name=f"Stale {code}",
            project_code=code,
            company=self.company,
            estimator=self.user,
            stage=stage,
            status=status or Opportunity.Status.OPEN,
            estimated_contract_value=Decimal("100000"),
            submission_date=today - timedelta(days=submission_offset_days),
        )

    def _stale_ids(self):
        return {r["id"] for r in reports.stale_opportunities(self.user)}

    # --- core threshold cases -----------------------------------------
    def test_submitted_20_days_ago_not_stale(self):
        opp = self._make_opp(
            "S20", stage=Opportunity.Stage.SUBMITTED, submission_offset_days=20
        )
        self.assertNotIn(opp.id, self._stale_ids())

    def test_submitted_31_days_ago_no_future_followup_is_stale(self):
        opp = self._make_opp(
            "S31", stage=Opportunity.Stage.SUBMITTED, submission_offset_days=31
        )
        self.assertIn(opp.id, self._stale_ids())

    def test_submitted_31_days_ago_with_pending_future_followup_not_stale(self):
        opp = self._make_opp(
            "S31F", stage=Opportunity.Stage.SUBMITTED, submission_offset_days=31
        )
        FollowUpTask.objects.create(
            opportunity=opp,
            assigned_to_user=self.user,
            subject="Chase",
            task_type=FollowUpTask.TaskType.CALL,
            status=FollowUpTask.Status.PENDING,
            due_date=timezone.localdate() + timedelta(days=5),
        )
        self.assertNotIn(opp.id, self._stale_ids())

    def test_past_due_pending_followup_still_stale(self):
        # A pending follow-up whose due_date is in the past does NOT
        # rescue the opportunity from staleness.
        opp = self._make_opp(
            "S31P", stage=Opportunity.Stage.SUBMITTED, submission_offset_days=40
        )
        FollowUpTask.objects.create(
            opportunity=opp,
            assigned_to_user=self.user,
            subject="Overdue chase",
            task_type=FollowUpTask.TaskType.CALL,
            status=FollowUpTask.Status.PENDING,
            due_date=timezone.localdate() - timedelta(days=3),
        )
        self.assertIn(opp.id, self._stale_ids())

    # --- excluded stages ----------------------------------------------
    def test_won_not_stale(self):
        opp = self._make_opp(
            "WON",
            stage=Opportunity.Stage.WON,
            submission_offset_days=90,
            status=Opportunity.Status.CLOSED,
        )
        self.assertNotIn(opp.id, self._stale_ids())

    def test_lost_not_stale(self):
        opp = self._make_opp(
            "LOST",
            stage=Opportunity.Stage.LOST,
            submission_offset_days=90,
            status=Opportunity.Status.CLOSED,
        )
        self.assertNotIn(opp.id, self._stale_ids())

    def test_lead_stage_not_stale(self):
        # lead is not an eligible stale stage even if old.
        opp = self._make_opp(
            "LEAD", stage=Opportunity.Stage.LEAD, submission_offset_days=90
        )
        self.assertNotIn(opp.id, self._stale_ids())

    def test_follow_up_and_negotiating_stages_are_eligible(self):
        fu = self._make_opp(
            "FU", stage=Opportunity.Stage.FOLLOW_UP, submission_offset_days=45
        )
        neg = self._make_opp(
            "NEG", stage=Opportunity.Stage.NEGOTIATING, submission_offset_days=45
        )
        stale = self._stale_ids()
        self.assertIn(fu.id, stale)
        self.assertIn(neg.id, stale)

    # --- archived exclusion -------------------------------------------
    def test_archived_not_stale(self):
        opp = self._make_opp(
            "ARCH", stage=Opportunity.Stage.SUBMITTED, submission_offset_days=60
        )
        opp.archived_at = timezone.now()
        opp.save(update_fields=["archived_at"])
        self.assertNotIn(opp.id, self._stale_ids())

    # --- metadata shape -----------------------------------------------
    def test_stale_metadata_fields(self):
        opp = self._make_opp(
            "META", stage=Opportunity.Stage.SUBMITTED, submission_offset_days=35
        )
        rows = [r for r in reports.stale_opportunities(self.user) if r["id"] == opp.id]
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertIn("stale_since_date", row)
        self.assertIn("days_since_submission", row)
        self.assertIn("last_followup_date", row)
        self.assertIn("next_followup_date", row)
        self.assertEqual(row["days_since_submission"], 35)
        self.assertEqual(
            row["stale_since_date"], date.today() - timedelta(days=35)
        )

    # --- submission date priority -------------------------------------
    def test_quote_submission_date_used_when_opp_date_missing(self):
        from apps.pipeline.models import Quote

        today = timezone.localdate()
        opp = Opportunity.objects.create(
            project_name="QuoteDated",
            project_code="QD-1",
            company=self.company,
            estimator=self.user,
            stage=Opportunity.Stage.SUBMITTED,
            estimated_contract_value=Decimal("100000"),
            submission_date=None,  # no opp-level date
        )
        Quote.objects.create(
            opportunity=opp,
            revision_number=1,
            quoted_value_ex_gst=Decimal("100000"),
            submission_date=today - timedelta(days=40),
            quote_status=Quote.QuoteStatus.SUBMITTED,
        )
        rows = [r for r in reports.stale_opportunities(self.user) if r["id"] == opp.id]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["days_since_submission"], 40)

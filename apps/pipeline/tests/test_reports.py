"""
Reporting service tests focused on the win/won-value figures — in
particular that an opportunity closed off via the mark_won endpoint
flows through to win-rate and won-value reporting.
"""
from decimal import Decimal

from rest_framework.test import APITestCase

from apps.pipeline.models import Company, Opportunity
from apps.pipeline.services import reports
from apps.users.models import AppUser


class WonReportingTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="report_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="ReportCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="ReportTarget",
            project_code="RPT-001",
            company=self.company,
            estimator=self.director,
            stage=Opportunity.Stage.SUBMITTED,
        )

    def _mark_won(self, value):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": value},
            format="json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_won_opportunity_appears_in_win_rate_by_estimator(self):
        self._mark_won("250000")
        rows = reports.win_rate_by_estimator(self.director)
        mine = [r for r in rows if r["estimator_id"] == self.director.id]
        self.assertEqual(len(mine), 1)
        row = mine[0]
        self.assertEqual(row["won"], 1)
        self.assertEqual(row["decided"], 1)
        self.assertEqual(row["won_value"], Decimal("250000.00"))
        self.assertEqual(row["win_rate_percent"], 100.0)

    def test_won_opportunity_appears_in_win_rate_by_company(self):
        self._mark_won("250000")
        rows = reports.win_rate_by_company(self.director)
        mine = [r for r in rows if r["company_id"] == self.company.id]
        self.assertEqual(len(mine), 1)
        row = mine[0]
        self.assertEqual(row["won"], 1)
        self.assertEqual(row["won_value"], Decimal("250000.00"))
        self.assertEqual(row["win_rate_percent"], 100.0)

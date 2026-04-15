"""
Quote auto-creation driven by Opportunity workflow.
"""
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, Opportunity, Quote
from apps.users.models import AppUser


class QuoteAutomationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director",
            password="x",
            role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="QACo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)

    # ----- helpers ----------------------------------------------------
    def _create_opp(
        self,
        *,
        project_code: str,
        stage: str = Opportunity.Stage.LEAD,
        value: Decimal | None = None,
    ) -> int:
        data = {
            "project_name": f"QA {project_code}",
            "project_code": project_code,
            "company": self.company.id,
            "stage": stage,
        }
        if value is not None:
            data["estimated_contract_value"] = str(value)
        resp = self.client.post("/api/opportunities/", data, format="json")
        self.assertEqual(
            resp.status_code, status.HTTP_201_CREATED, resp.data
        )
        return resp.data["id"]

    def _quotes(self, opp_id: int):
        return Quote.objects.filter(opportunity_id=opp_id).order_by("revision_number")

    # ----- no-op cases ------------------------------------------------
    def test_no_quote_for_ineligible_stage(self):
        opp_id = self._create_opp(
            project_code="QA-L",
            stage=Opportunity.Stage.LEAD,
            value=Decimal("500000.00"),
        )
        self.assertEqual(self._quotes(opp_id).count(), 0)

    def test_no_quote_when_value_missing(self):
        opp_id = self._create_opp(
            project_code="QA-NV",
            stage=Opportunity.Stage.PRICING,
            value=None,
        )
        self.assertEqual(self._quotes(opp_id).count(), 0)

    def test_ordinary_edit_does_not_duplicate_quote(self):
        opp_id = self._create_opp(
            project_code="QA-ED",
            stage=Opportunity.Stage.PRICING,
            value=Decimal("500000.00"),
        )
        self.assertEqual(self._quotes(opp_id).count(), 1)
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"notes": "just a note"},
            format="json",
        )
        self.assertEqual(self._quotes(opp_id).count(), 1)

    def test_stage_exit_does_not_create_new_quote(self):
        opp_id = self._create_opp(
            project_code="QA-EX",
            stage=Opportunity.Stage.PRICING,
            value=Decimal("500000.00"),
        )
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.LEAD},
            format="json",
        )
        self.assertEqual(self._quotes(opp_id).count(), 1)

    # ----- creation cases ---------------------------------------------
    def test_rev_1_created_when_opp_created_in_pricing(self):
        opp_id = self._create_opp(
            project_code="QA-P1",
            stage=Opportunity.Stage.PRICING,
            value=Decimal("500000.00"),
        )
        quotes = self._quotes(opp_id)
        self.assertEqual(quotes.count(), 1)
        q = quotes.first()
        self.assertEqual(q.revision_number, 1)
        self.assertEqual(q.quoted_value_ex_gst, Decimal("500000.00"))
        self.assertEqual(q.quote_status, Quote.QuoteStatus.DRAFT)
        self.assertEqual(q.quote_reference, "QA-P1-R1")

    def test_rev_1_created_with_submitted_status_when_opp_created_in_submitted(self):
        opp_id = self._create_opp(
            project_code="QA-S1",
            stage=Opportunity.Stage.SUBMITTED,
            value=Decimal("500000.00"),
        )
        q = self._quotes(opp_id).first()
        self.assertEqual(q.revision_number, 1)
        self.assertEqual(q.quote_status, Quote.QuoteStatus.SUBMITTED)

    def test_entering_pricing_later_creates_rev_1(self):
        opp_id = self._create_opp(
            project_code="QA-LP",
            stage=Opportunity.Stage.LEAD,
            value=Decimal("500000.00"),
        )
        self.assertEqual(self._quotes(opp_id).count(), 0)
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.PRICING},
            format="json",
        )
        self.assertEqual(self._quotes(opp_id).count(), 1)

    # ----- revision cases ---------------------------------------------
    def test_value_change_creates_next_revision(self):
        opp_id = self._create_opp(
            project_code="QA-V",
            stage=Opportunity.Stage.PRICING,
            value=Decimal("500000.00"),
        )
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"estimated_contract_value": "600000.00"},
            format="json",
        )
        quotes = self._quotes(opp_id)
        self.assertEqual(quotes.count(), 2)
        self.assertEqual(
            [q.revision_number for q in quotes], [1, 2]
        )
        self.assertEqual(
            quotes.last().quoted_value_ex_gst, Decimal("600000.00")
        )

    def test_resubmission_creates_next_revision_without_value_change(self):
        opp_id = self._create_opp(
            project_code="QA-R",
            stage=Opportunity.Stage.PRICING,
            value=Decimal("500000.00"),
        )
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        quotes = self._quotes(opp_id)
        self.assertEqual(quotes.count(), 2)
        self.assertEqual(quotes.last().quote_status, Quote.QuoteStatus.SUBMITTED)

    def test_second_resubmission_after_followup_creates_another_revision(self):
        opp_id = self._create_opp(
            project_code="QA-R2",
            stage=Opportunity.Stage.SUBMITTED,
            value=Decimal("500000.00"),
        )
        # submitted → follow_up (no new quote — ineligible stage)
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.FOLLOW_UP},
            format="json",
        )
        self.assertEqual(self._quotes(opp_id).count(), 1)
        # follow_up → submitted (resubmission)
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        self.assertEqual(self._quotes(opp_id).count(), 2)

    # ----- API shape check --------------------------------------------
    def test_quotes_endpoint_returns_auto_created_quote(self):
        opp_id = self._create_opp(
            project_code="QA-API",
            stage=Opportunity.Stage.PRICING,
            value=Decimal("500000.00"),
        )
        resp = self.client.get(f"/api/quotes/?opportunity={opp_id}")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["count"], 1)
        row = resp.data["results"][0]
        self.assertEqual(row["revision_number"], 1)
        # nested opportunity with project_id alias
        self.assertEqual(row["opportunity"]["id"], opp_id)
        self.assertEqual(row["opportunity"]["project_id"], "QA-API")
        # friendly aliases
        self.assertEqual(Decimal(row["value"]), Decimal("500000.00"))
        self.assertIn("submitted_at", row)
        self.assertIn("created_at", row)

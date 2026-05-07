"""
Quote revision workflow + opportunity-specific filtering.
"""
from decimal import Decimal

from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import Company, Opportunity, Quote
from apps.users.models import AppUser


class QuoteRevisionAndFilterTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="qrf_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="QRFCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)

    # ---- revision creation via value change --------------------------
    def test_rev1_created_on_pricing_then_rev2_on_value_change(self):
        # Create opp at pricing stage with a value → rev 1
        resp = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "Rev Test",
                "project_code": "QREV-01",
                "company": self.company.id,
                "stage": Opportunity.Stage.PRICING,
                "estimated_contract_value": "500000.00",
                "estimated_margin_percent": "12.00",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        opp_id = resp.data["id"]
        quotes = Quote.objects.filter(opportunity_id=opp_id).order_by(
            "revision_number"
        )
        self.assertEqual(quotes.count(), 1)
        r1 = quotes.first()
        self.assertEqual(r1.revision_number, 1)
        self.assertEqual(r1.quoted_value_ex_gst, Decimal("500000.00"))
        self.assertEqual(r1.quoted_margin_percent, Decimal("12.00"))
        self.assertIn("QREV-01-R1", r1.quote_reference)

        # Change value → rev 2
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"estimated_contract_value": "520000.00"},
            format="json",
        )
        quotes = Quote.objects.filter(opportunity_id=opp_id).order_by(
            "revision_number"
        )
        self.assertEqual(quotes.count(), 2)
        r2 = quotes.last()
        self.assertEqual(r2.revision_number, 2)
        self.assertEqual(r2.quoted_value_ex_gst, Decimal("520000.00"))
        self.assertIn("QREV-01-R2", r2.quote_reference)

        # Old rev 1 is still intact
        r1.refresh_from_db()
        self.assertEqual(r1.quoted_value_ex_gst, Decimal("500000.00"))

    def test_unrelated_edit_does_not_create_revision(self):
        resp = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "NoRev",
                "project_code": "QREV-02",
                "company": self.company.id,
                "stage": Opportunity.Stage.PRICING,
                "estimated_contract_value": "300000.00",
            },
            format="json",
        )
        opp_id = resp.data["id"]
        self.assertEqual(
            Quote.objects.filter(opportunity_id=opp_id).count(), 1
        )
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"notes": "just a note"},
            format="json",
        )
        self.assertEqual(
            Quote.objects.filter(opportunity_id=opp_id).count(), 1
        )

    # ---- latest_quote on opportunity detail --------------------------
    def test_latest_quote_is_highest_revision(self):
        resp = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "LatestQ",
                "project_code": "QREV-03",
                "company": self.company.id,
                "stage": Opportunity.Stage.PRICING,
                "estimated_contract_value": "400000.00",
            },
            format="json",
        )
        opp_id = resp.data["id"]
        # Trigger rev 2
        self.client.patch(
            f"/api/opportunities/{opp_id}/",
            {"estimated_contract_value": "410000.00"},
            format="json",
        )
        opp_detail = self.client.get(
            f"/api/opportunities/{opp_id}/"
        ).data
        lq = opp_detail.get("latest_quote")
        self.assertIsNotNone(lq)
        self.assertEqual(lq["revision_number"], 2)

    # ---- filtering: ?opportunity= and ?opportunity_id= ---------------
    def test_filter_by_opportunity(self):
        resp_a = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "FilterA",
                "project_code": "QFILT-A",
                "company": self.company.id,
                "stage": Opportunity.Stage.PRICING,
                "estimated_contract_value": "100000.00",
            },
            format="json",
        )
        resp_b = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "FilterB",
                "project_code": "QFILT-B",
                "company": self.company.id,
                "stage": Opportunity.Stage.PRICING,
                "estimated_contract_value": "200000.00",
            },
            format="json",
        )
        opp_a = resp_a.data["id"]
        opp_b = resp_b.data["id"]

        # ?opportunity=<a>
        resp = self.client.get(f"/api/quotes/?opportunity={opp_a}")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["opportunity"], opp_a)

        # ?opportunity_id=<b>  (alias — common frontend convention)
        resp = self.client.get(f"/api/quotes/?opportunity_id={opp_b}")
        self.assertEqual(resp.data["count"], 1)
        self.assertEqual(resp.data["results"][0]["opportunity"], opp_b)

    def test_unrelated_quotes_excluded(self):
        resp_a = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "ExclA",
                "project_code": "QEXCL-A",
                "company": self.company.id,
                "stage": Opportunity.Stage.PRICING,
                "estimated_contract_value": "100000.00",
            },
            format="json",
        )
        self.client.post(
            "/api/opportunities/",
            {
                "project_name": "ExclB",
                "project_code": "QEXCL-B",
                "company": self.company.id,
                "stage": Opportunity.Stage.PRICING,
                "estimated_contract_value": "200000.00",
            },
            format="json",
        )
        opp_a = resp_a.data["id"]
        resp = self.client.get(
            f"/api/quotes/?opportunity={opp_a}&page_size=500"
        )
        for row in resp.data["results"]:
            self.assertEqual(
                row["opportunity"],
                opp_a,
                f"Quote {row['id']} belongs to opp {row['opportunity']}, "
                f"expected {opp_a}",
            )

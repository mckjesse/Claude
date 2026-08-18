"""
Grouped project outcome: close related opportunities as lost when one
wins.
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import (
    ActivityLog,
    Company,
    LossReason,
    Opportunity,
)
from apps.users.models import AppUser


class CloseRelatedAsLostTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="grp_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.co_a = Company.objects.create(
            name="Builder A", company_type=Company.Type.BUILDER,
        )
        cls.co_b = Company.objects.create(
            name="Builder B", company_type=Company.Type.BUILDER,
        )
        cls.co_c = Company.objects.create(
            name="Builder C", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        # Same project priced to three builders.
        self.won = Opportunity.objects.create(
            project_name="Shared Project",
            project_code="SHARED-001",
            company=self.co_a,
            estimator=self.director,
            stage=Opportunity.Stage.WON,
            status=Opportunity.Status.CLOSED,
            estimated_contract_value=Decimal("500000"),
            final_awarded_value=Decimal("490000"),
        )
        self.open_b = Opportunity.objects.create(
            project_name="Shared Project",
            project_code="SHARED-001",
            company=self.co_b,
            estimator=self.director,
            stage=Opportunity.Stage.SUBMITTED,
            estimated_contract_value=Decimal("520000"),
        )
        self.open_c = Opportunity.objects.create(
            project_name="Shared Project",
            project_code="SHARED-001",
            company=self.co_c,
            estimator=self.director,
            stage=Opportunity.Stage.PRICING,
            estimated_contract_value=Decimal("510000"),
        )

    def test_closes_related_open_opps_as_lost(self):
        resp = self.client.post(
            f"/api/opportunities/{self.won.id}/close_related_as_lost/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["closed"]), 2)
        self.open_b.refresh_from_db()
        self.open_c.refresh_from_db()
        self.assertEqual(self.open_b.stage, Opportunity.Stage.LOST)
        self.assertEqual(self.open_b.status, Opportunity.Status.CLOSED)
        self.assertEqual(self.open_c.stage, Opportunity.Stage.LOST)
        self.assertEqual(self.open_c.status, Opportunity.Status.CLOSED)

    def test_creates_loss_reasons_with_winning_builder(self):
        self.client.post(
            f"/api/opportunities/{self.won.id}/close_related_as_lost/",
            format="json",
        )
        lr_b = LossReason.objects.get(opportunity=self.open_b)
        self.assertEqual(
            lr_b.reason_category, LossReason.Category.PROJECT_WON_OTHER
        )
        self.assertEqual(lr_b.competitor_name, "Builder A")

    def test_does_not_close_the_won_opportunity_itself(self):
        self.client.post(
            f"/api/opportunities/{self.won.id}/close_related_as_lost/",
            format="json",
        )
        self.won.refresh_from_db()
        self.assertEqual(self.won.stage, Opportunity.Stage.WON)

    def test_returns_affected_opportunities_in_response(self):
        resp = self.client.post(
            f"/api/opportunities/{self.won.id}/close_related_as_lost/",
            format="json",
        )
        ids = [c["id"] for c in resp.data["closed"]]
        self.assertIn(self.open_b.id, ids)
        self.assertIn(self.open_c.id, ids)
        self.assertNotIn(self.won.id, ids)

    def test_rejects_if_opportunity_is_not_won(self):
        resp = self.client.post(
            f"/api/opportunities/{self.open_b.id}/close_related_as_lost/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_noop_when_no_related_open(self):
        # Close both related first.
        self.open_b.stage = Opportunity.Stage.LOST
        self.open_b.status = Opportunity.Status.CLOSED
        self.open_b.save()
        self.open_c.stage = Opportunity.Stage.LOST
        self.open_c.status = Opportunity.Status.CLOSED
        self.open_c.save()
        resp = self.client.post(
            f"/api/opportunities/{self.won.id}/close_related_as_lost/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["closed"], [])

    def test_idempotent_loss_reason_update(self):
        # Run twice — the second run should not fail because
        # LossReason uses update_or_create.
        self.client.post(
            f"/api/opportunities/{self.won.id}/close_related_as_lost/",
            format="json",
        )
        # Reopen one and re-run.
        self.open_b.stage = Opportunity.Stage.FOLLOW_UP
        self.open_b.status = Opportunity.Status.OPEN
        self.open_b.save()
        resp = self.client.post(
            f"/api/opportunities/{self.won.id}/close_related_as_lost/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data["closed"]), 1)
        self.assertEqual(
            LossReason.objects.filter(opportunity=self.open_b).count(), 1
        )

    def test_archived_related_opportunity_is_left_alone(self):
        # Archived opportunities are soft-deleted. A bulk workflow must
        # not reach back into them.
        self.open_c.archived_at = timezone.now()
        self.open_c.archived_by = self.director
        self.open_c.save(update_fields=["archived_at", "archived_by"])

        resp = self.client.post(
            f"/api/opportunities/{self.won.id}/close_related_as_lost/",
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        closed_ids = [row["id"] for row in resp.data["closed"]]
        self.assertNotIn(self.open_c.id, closed_ids)
        self.assertIn(self.open_b.id, closed_ids)

        self.open_c.refresh_from_db()
        self.assertEqual(self.open_c.stage, Opportunity.Stage.PRICING)
        self.assertEqual(self.open_c.status, Opportunity.Status.OPEN)
        self.assertFalse(
            LossReason.objects.filter(opportunity=self.open_c).exists()
        )

    def test_stage_changed_activity_records_the_real_previous_stage(self):
        # open_b is at "submitted" and open_c at "pricing" — the log must
        # say so, not report a hardcoded stage.
        self.client.post(
            f"/api/opportunities/{self.won.id}/close_related_as_lost/",
            format="json",
        )
        for opp, expected in (
            (self.open_b, "Submitted"),
            (self.open_c, "Pricing"),
        ):
            description = (
                ActivityLog.objects.filter(
                    opportunity=opp, activity_type="stage_changed"
                )
                .values_list("description", flat=True)
                .first()
            )
            self.assertEqual(
                description, f"Stage changed from {expected} to Lost."
            )

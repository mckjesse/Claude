"""
Opportunity creation + validation + mark_won / mark_lost.
"""
from decimal import Decimal

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from apps.pipeline.models import (
    Company,
    FollowUpTask,
    LossReason,
    Opportunity,
)
from apps.users.models import AppUser


class OpportunityCreationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="Test Builder", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)

    def test_create_opportunity_succeeds(self):
        resp = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "Test Project",
                "project_code": "TEST-001",
                "company": self.company.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["project_name"], "Test Project")
        # Default stage is lead and status is open
        self.assertEqual(resp.data["stage"], Opportunity.Stage.LEAD)
        self.assertEqual(resp.data["status"], Opportunity.Status.OPEN)

    def test_create_opportunity_requires_company(self):
        resp = self.client.post(
            "/api/opportunities/",
            {"project_name": "No Company"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("company", resp.data)

    def test_create_opportunity_requires_project_code(self):
        # project_code is the Project ID — the canonical human identifier.
        resp = self.client.post(
            "/api/opportunities/",
            {"project_name": "No ID", "company": self.company.id},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("project_code", resp.data)

    def test_same_project_code_same_company_is_blocked(self):
        self.client.post(
            "/api/opportunities/",
            {
                "project_name": "First",
                "project_code": "UNIQ-1",
                "company": self.company.id,
            },
            format="json",
        )
        resp = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "Dupe",
                "project_code": "UNIQ-1",
                "company": self.company.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_same_project_code_different_company_is_allowed(self):
        other_company = Company.objects.create(
            name="Other Builder", company_type=Company.Type.BUILDER,
        )
        self.client.post(
            "/api/opportunities/",
            {
                "project_name": "Builder A bid",
                "project_code": "MULTI-1",
                "company": self.company.id,
            },
            format="json",
        )
        resp = self.client.post(
            "/api/opportunities/",
            {
                "project_name": "Builder B bid",
                "project_code": "MULTI-1",
                "company": other_company.id,
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)


class OpportunityValidationTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="Validator Co", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="Validation Target",
            project_code="VAL-001",
            company=self.company,
            estimator=self.director,
        )

    def test_stage_won_requires_final_awarded_value(self):
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.WON},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("final_awarded_value", resp.data)

    def test_probability_percent_must_be_0_to_100(self):
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"probability_percent": 150},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("probability_percent", resp.data)


class MarkWonTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="MarkWonCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="WinTarget",
            project_code="WIN-001",
            company=self.company,
            estimator=self.director,
        )

    def test_mark_won_requires_final_awarded_value(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("final_awarded_value", resp.data)

    def test_mark_won_rejects_negative_value(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "-500"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_won_rejects_zero_value(self):
        # final_awarded_value must be strictly greater than 0.
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "0"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("final_awarded_value", resp.data)

    def test_mark_won_saves_award_date_and_notes(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {
                "final_awarded_value": "250000",
                "award_date": "2026-07-30",
                "notes": "Awarded after follow-up",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.final_awarded_value, Decimal("250000"))
        self.assertEqual(str(self.opp.award_date), "2026-07-30")
        self.assertIn("Awarded after follow-up", self.opp.notes)
        # Response nests the updated opportunity plus cleared-followup info.
        self.assertEqual(resp.data["opportunity"]["stage"], Opportunity.Stage.WON)
        self.assertEqual(resp.data["opportunity"]["award_date"], "2026-07-30")
        self.assertEqual(resp.data["cleared_followups_count"], 0)
        self.assertEqual(resp.data["cleared_followup_ids"], [])

    def test_lost_opportunity_cannot_be_marked_won(self):
        self.opp.stage = Opportunity.Stage.LOST
        self.opp.status = Opportunity.Status.CLOSED
        self.opp.save(update_fields=["stage", "status"])
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "250000"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.LOST)

    def test_archived_opportunity_cannot_be_marked_won(self):
        from django.utils import timezone

        self.opp.archived_at = timezone.now()
        self.opp.save(update_fields=["archived_at"])
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "250000"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.opp.refresh_from_db()
        self.assertNotEqual(self.opp.stage, Opportunity.Stage.WON)

    def test_mark_won_sets_stage_status_and_value(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_won/",
            {"final_awarded_value": "500000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.WON)
        self.assertEqual(self.opp.status, Opportunity.Status.CLOSED)
        self.assertEqual(self.opp.final_awarded_value, Decimal("500000.00"))

    def test_direct_patch_to_won_auto_closes_status(self):
        # PATCH stage=won with final_awarded_value should still force
        # status=closed, even though this path bypasses mark_won.
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.WON, "final_awarded_value": "123000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.WON)
        self.assertEqual(self.opp.status, Opportunity.Status.CLOSED)


class MarkLostTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="director", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="MarkLostCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="LossTarget",
            project_code="LOSS-001",
            company=self.company,
            estimator=self.director,
        )

    def test_mark_lost_requires_reason_category(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reason_category", resp.data)

    def test_mark_lost_rejects_invalid_reason_category(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {"reason_category": "not-a-real-category"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_mark_lost_creates_loss_reason_and_closes_opportunity(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {
                "reason_category": LossReason.Category.PRICE,
                "competitor_name": "BigBuild Co",
                "reason_detail": "Client went cheaper.",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.LOST)
        self.assertEqual(self.opp.status, Opportunity.Status.CLOSED)

        lr = LossReason.objects.get(opportunity=self.opp)
        self.assertEqual(lr.reason_category, LossReason.Category.PRICE)
        self.assertEqual(lr.competitor_name, "BigBuild Co")

    def test_mark_lost_is_idempotent(self):
        # First call creates the LossReason
        self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {"reason_category": LossReason.Category.PRICE},
            format="json",
        )
        # Second call updates the same row, does not create a duplicate
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {
                "reason_category": LossReason.Category.SCOPE,
                "competitor_name": "Updated Rival",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(
            LossReason.objects.filter(opportunity=self.opp).count(), 1
        )
        lr = LossReason.objects.get(opportunity=self.opp)
        self.assertEqual(lr.reason_category, LossReason.Category.SCOPE)
        self.assertEqual(lr.competitor_name, "Updated Rival")

    def test_direct_patch_to_lost_is_rejected_without_existing_reason(self):
        # Direct PATCH must not be able to set stage=lost without a
        # LossReason being recorded. Callers are forced through
        # POST /mark_lost/.
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.LOST},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stage", resp.data)
        self.opp.refresh_from_db()
        # State is unchanged
        self.assertNotEqual(self.opp.stage, Opportunity.Stage.LOST)

    def test_direct_patch_to_lost_works_when_reason_already_exists(self):
        # Having already marked lost via the canonical action, a
        # follow-up PATCH that re-states stage=lost is harmless.
        self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {"reason_category": LossReason.Category.PRICE},
            format="json",
        )
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.LOST, "notes": "post-loss note"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.LOST)
        self.assertEqual(self.opp.status, Opportunity.Status.CLOSED)

    def test_direct_patch_out_of_lost_is_blocked(self):
        # Trying to PATCH stage away from 'lost' must be rejected.
        self.client.post(
            f"/api/opportunities/{self.opp.id}/mark_lost/",
            {"reason_category": LossReason.Category.PRICE},
            format="json",
        )
        resp = self.client.patch(
            f"/api/opportunities/{self.opp.id}/",
            {"stage": Opportunity.Stage.LEAD},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("stage", resp.data)


class ReopenTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="reopen_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="ReopenCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="ReopenTarget",
            project_code=f"RE-{self.id()[-6:]}",
            company=self.company,
            estimator=self.director,
            stage=Opportunity.Stage.LOST,
            status=Opportunity.Status.CLOSED,
        )
        LossReason.objects.create(
            opportunity=self.opp,
            reason_category=LossReason.Category.PRICE,
            reason_detail="Original loss.",
        )

    def test_reopen_sets_stage_follow_up_and_status_open(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.FOLLOW_UP)
        self.assertEqual(self.opp.status, Opportunity.Status.OPEN)

    def test_reopen_preserves_loss_reason(self):
        self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        lr = LossReason.objects.get(opportunity=self.opp)
        self.assertEqual(lr.reason_category, LossReason.Category.PRICE)
        self.assertEqual(lr.reason_detail, "Original loss.")

    def test_reopen_creates_activity_entries(self):
        from apps.pipeline.models import ActivityLog

        before = ActivityLog.objects.filter(opportunity=self.opp).count()
        self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        after = ActivityLog.objects.filter(opportunity=self.opp).count()
        self.assertEqual(after - before, 2)  # stage_changed + reopened

    def test_reopen_rejects_non_terminal_opportunity(self):
        self.opp.stage = Opportunity.Stage.PRICING
        self.opp.status = Opportunity.Status.OPEN
        self.opp.save()
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_reopen_works_on_won_opportunity(self):
        self.opp.stage = Opportunity.Stage.WON
        self.opp.final_awarded_value = "500000.00"
        self.opp.save()
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/reopen/", format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.FOLLOW_UP)
        self.assertEqual(self.opp.status, Opportunity.Status.OPEN)


class ArchiveAndDeleteTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="archive_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="ArchiveCo", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)
        self.opp = Opportunity.objects.create(
            project_name="ArchiveTarget",
            project_code="ARC-001",
            company=self.company,
            estimator=self.director,
            stage=Opportunity.Stage.PRICING,
            estimated_contract_value=Decimal("250000.00"),
        )
        # Create child records so we can verify cascade filtering.
        from apps.pipeline.models import FollowUpTask, Quote

        self.quote = Quote.objects.create(
            opportunity=self.opp,
            revision_number=1,
            quoted_value_ex_gst=Decimal("250000.00"),
            quote_reference="ARC-001-R1",
        )
        self.task = FollowUpTask.objects.create(
            opportunity=self.opp,
            assigned_to_user=self.director,
            subject="Chase builder",
            task_type=FollowUpTask.TaskType.CALL,
            due_date="2099-01-01",
        )

    def test_archive_sets_fields_and_hides_from_list(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertIsNotNone(self.opp.archived_at)
        self.assertEqual(self.opp.archived_by, self.director)
        resp = self.client.get("/api/opportunities/")
        self.assertNotIn(
            self.opp.id, [r["id"] for r in resp.data["results"]]
        )

    def test_archive_preserves_stage_and_status(self):
        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        self.opp.refresh_from_db()
        self.assertEqual(self.opp.stage, Opportunity.Stage.PRICING)
        self.assertEqual(self.opp.status, Opportunity.Status.OPEN)

    def test_archive_rejected_if_already_archived(self):
        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_list_archived_true_returns_archived_only(self):
        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        resp = self.client.get("/api/opportunities/?archived=true")
        self.assertIn(
            self.opp.id, [r["id"] for r in resp.data["results"]]
        )

    def test_list_archived_all_returns_both(self):
        active = Opportunity.objects.create(
            project_name="StillActive",
            project_code="ARC-002",
            company=self.company,
            estimator=self.director,
        )
        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        resp = self.client.get("/api/opportunities/?archived=all")
        ids = [r["id"] for r in resp.data["results"]]
        self.assertIn(self.opp.id, ids)
        self.assertIn(active.id, ids)

    def test_restore_clears_archive_fields(self):
        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/restore/", format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.opp.refresh_from_db()
        self.assertIsNone(self.opp.archived_at)
        self.assertIsNone(self.opp.archived_by)

    def test_restore_on_non_archived_is_rejected(self):
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/restore/", format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_delete_on_non_archived_is_rejected(self):
        resp = self.client.delete(f"/api/opportunities/{self.opp.id}/")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertTrue(
            Opportunity.objects.filter(pk=self.opp.pk).exists()
        )

    def test_delete_works_after_archive(self):
        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        resp = self.client.delete(f"/api/opportunities/{self.opp.id}/")
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Opportunity.objects.filter(pk=self.opp.pk).exists()
        )

    def test_estimator_can_archive(self):
        estimator = AppUser.objects.create_user(
            username="est_arch", password="x", role=AppUser.Role.ESTIMATOR,
        )
        self.client.force_authenticate(user=estimator)
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_read_only_cannot_archive(self):
        ro = AppUser.objects.create_user(
            username="ro_arch", password="x", role=AppUser.Role.READ_ONLY,
        )
        self.client.force_authenticate(user=ro)
        resp = self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    # ---- child-record cascade filtering -----------------------------
    def test_archive_hides_quotes_from_default_list(self):
        resp = self.client.get("/api/quotes/")
        ids_before = [r["id"] for r in resp.data["results"]]
        self.assertIn(self.quote.id, ids_before)

        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        resp = self.client.get("/api/quotes/")
        ids_after = [r["id"] for r in resp.data["results"]]
        self.assertNotIn(self.quote.id, ids_after)

    def test_archive_hides_followups_from_default_list(self):
        resp = self.client.get("/api/followups/")
        ids_before = [r["id"] for r in resp.data["results"]]
        self.assertIn(self.task.id, ids_before)

        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        resp = self.client.get("/api/followups/")
        ids_after = [r["id"] for r in resp.data["results"]]
        self.assertNotIn(self.task.id, ids_after)

    def test_archive_preserves_activity_log_visibility(self):
        from apps.pipeline.models import ActivityLog

        # The archive action itself creates an activity log entry.
        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        resp = self.client.get(
            f"/api/activities/?opportunity={self.opp.id}"
        )
        self.assertGreater(resp.data["count"], 0)

    def test_restore_unhides_quotes_and_followups(self):
        self.client.post(
            f"/api/opportunities/{self.opp.id}/archive/", format="json"
        )
        self.client.post(
            f"/api/opportunities/{self.opp.id}/restore/", format="json"
        )
        resp_q = self.client.get("/api/quotes/")
        resp_f = self.client.get("/api/followups/")
        self.assertIn(
            self.quote.id, [r["id"] for r in resp_q.data["results"]]
        )
        self.assertIn(
            self.task.id, [r["id"] for r in resp_f.data["results"]]
        )


class TerminalTransitionGuardTests(APITestCase):
    """
    ``reopen`` is the only sanctioned door out of a terminal stage. The
    serializer enforces that on the PATCH path and mark_won already
    rejects a lost opportunity; mark_lost must reject a won one too, or
    it leaves a lost row still carrying its final_awarded_value.
    """

    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="terminal_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="Terminal Builder", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)

    def _opportunity(self, code):
        return Opportunity.objects.create(
            project_name="Terminal Project",
            project_code=code,
            company=self.company,
            estimator=self.director,
            stage=Opportunity.Stage.SUBMITTED,
            estimated_contract_value=Decimal("250000.00"),
        )

    def test_mark_lost_rejects_a_won_opportunity(self):
        opp = self._opportunity("TERM-002")
        self.client.post(
            f"/api/opportunities/{opp.id}/mark_won/",
            {"final_awarded_value": "260000.00"},
            format="json",
        )
        resp = self.client.post(
            f"/api/opportunities/{opp.id}/mark_lost/",
            {"reason_category": "price"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reopen", resp.data["detail"].lower())

        opp.refresh_from_db()
        self.assertEqual(opp.stage, Opportunity.Stage.WON)
        self.assertFalse(LossReason.objects.filter(opportunity=opp).exists())

    def test_mark_won_rejects_a_lost_opportunity(self):
        opp = self._opportunity("TERM-001")
        self.client.post(
            f"/api/opportunities/{opp.id}/mark_lost/",
            {"reason_category": "price"},
            format="json",
        )
        resp = self.client.post(
            f"/api/opportunities/{opp.id}/mark_won/",
            {"final_awarded_value": "260000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("reopen", resp.data["detail"].lower())

        opp.refresh_from_db()
        self.assertEqual(opp.stage, Opportunity.Stage.LOST)
        self.assertIsNone(opp.final_awarded_value)

    def test_reopen_then_mark_lost_is_allowed(self):
        # The guard must not block the sanctioned route.
        opp = self._opportunity("TERM-003")
        self.client.post(
            f"/api/opportunities/{opp.id}/mark_won/",
            {"final_awarded_value": "260000.00"},
            format="json",
        )
        self.client.post(f"/api/opportunities/{opp.id}/reopen/", format="json")
        resp = self.client.post(
            f"/api/opportunities/{opp.id}/mark_lost/",
            {"reason_category": "price"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        opp.refresh_from_db()
        self.assertEqual(opp.stage, Opportunity.Stage.LOST)


class ActionResponseFreshnessTests(APITestCase):
    """
    ``get_object()`` primes the prefetch cache for quotes and tasks.
    Quote automation then writes a quote and the terminal-follow-up
    sweep cancels tasks — neither visible to that cache. The action must
    drop it before serialising, or it reports a null latest_quote for a
    quote it just created and keeps advertising a cancelled follow-up.
    """

    @classmethod
    def setUpTestData(cls):
        cls.director = AppUser.objects.create_user(
            username="fresh_dir", password="x", role=AppUser.Role.DIRECTOR,
        )
        cls.company = Company.objects.create(
            name="Fresh Builder", company_type=Company.Type.BUILDER,
        )

    def setUp(self):
        self.client.force_authenticate(user=self.director)

    def _opportunity(self, code):
        return Opportunity.objects.create(
            project_name="Fresh Project",
            project_code=code,
            company=self.company,
            estimator=self.director,
            stage=Opportunity.Stage.SUBMITTED,
            estimated_contract_value=Decimal("300000.00"),
        )

    def test_mark_won_response_includes_the_auto_created_quote(self):
        opp = self._opportunity("FRESH-001")
        resp = self.client.post(
            f"/api/opportunities/{opp.id}/mark_won/",
            {"final_awarded_value": "310000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(opp.quotes.count(), 1)
        latest = resp.data["opportunity"]["latest_quote"]
        self.assertIsNotNone(latest)
        self.assertEqual(latest["quoted_value_ex_gst"], "310000.00")
        self.assertEqual(latest["quote_status"], "accepted")

    def test_mark_lost_response_includes_the_auto_created_quote(self):
        opp = self._opportunity("FRESH-002")
        resp = self.client.post(
            f"/api/opportunities/{opp.id}/mark_lost/",
            {"reason_category": "price"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(opp.quotes.count(), 1)
        latest = resp.data["opportunity"]["latest_quote"]
        self.assertIsNotNone(latest)
        self.assertEqual(latest["quote_status"], "unsuccessful")

    def test_mark_won_response_does_not_advertise_a_cancelled_followup(self):
        # The terminal sweep cancels outstanding follow-ups inside the
        # transaction; next_followup must not still show one.
        opp = self._opportunity("FRESH-003")
        FollowUpTask.objects.create(
            opportunity=opp,
            assigned_to_user=self.director,
            subject="Chase the builder",
            task_type=FollowUpTask.TaskType.CALL,
            due_date=timezone.localdate(),
            priority=FollowUpTask.Priority.HIGH,
            status=FollowUpTask.Status.PENDING,
        )
        resp = self.client.post(
            f"/api/opportunities/{opp.id}/mark_won/",
            {"final_awarded_value": "310000.00"},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertGreaterEqual(resp.data["cleared_followups_count"], 1)
        self.assertIsNone(resp.data["opportunity"]["next_followup"])

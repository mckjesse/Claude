"""
One-shot proof test: drive a real opportunity stage transition through
the same DRF view code path the API uses, and show that a Quote record
appears with each field mapped from the expected opportunity source.

Usage:
    python manage.py prove_quote_creation

Picks (or creates) an Opportunity that has all four "source" fields
populated — project_code, estimated_contract_value,
estimated_margin_percent, submission_date — so every mapping can be
verified in a single run. PATCHes stage to "submitted" via
OpportunityViewSet (same path the React frontend hits), then prints:

  SOURCE      — values on the opportunity before the patch
  QUOTE       — fields on the created quote
  MAPPING     — PASS/FAIL for each Opportunity → Quote mapping

This command is throwaway / debug only; it is not used in production
flow.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.management.base import BaseCommand
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.pipeline.models import Company, Opportunity, Quote
from apps.pipeline.views import OpportunityViewSet
from apps.users.models import AppUser


class Command(BaseCommand):
    help = (
        "Drive an opportunity with fully populated source fields "
        "through OpportunityViewSet and verify every field of the "
        "auto-created Quote is mapped from the expected source."
    )

    def handle(self, *args, **options):
        actor = (
            AppUser.objects.filter(role=AppUser.Role.DIRECTOR).first()
            or AppUser.objects.filter(is_superuser=True).first()
            or AppUser.objects.first()
        )
        if actor is None:
            self.stdout.write(self.style.ERROR(
                "No AppUser exists. Run `python manage.py seed_demo` first."
            ))
            return

        opp = self._prepare_opportunity()
        self._print_source_fields(opp)

        response = self._patch_stage_submitted(opp.id, actor)
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(
            'PATCH /api/opportunities/{id}/  with {"stage": "submitted"}'
        )
        self.stdout.write("(driven through OpportunityViewSet — same path the API uses)")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  HTTP status: {response.status_code}")
        if response.status_code >= 400:
            self.stdout.write(self.style.ERROR(f"  Response: {response.data}"))
            return

        opp.refresh_from_db()
        new_quote = (
            Quote.objects.filter(opportunity=opp)
            .order_by("-revision_number")
            .first()
        )
        if new_quote is None:
            self.stdout.write(self.style.WARNING(
                "No quote was created — auto-creation did NOT fire."
            ))
            return

        self._print_quote_fields(new_quote)
        self._print_mapping_assertions(opp, new_quote)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _prepare_opportunity(self) -> Opportunity:
        """
        Use an existing opportunity that has every source field
        populated and no quote yet; otherwise create one. Either way
        the object is guaranteed to carry project_code,
        estimated_contract_value, estimated_margin_percent and
        submission_date so every mapping has something to compare.
        """
        candidate = (
            Opportunity.objects.filter(
                estimated_contract_value__gt=0,
                estimated_margin_percent__isnull=False,
                submission_date__isnull=False,
                quotes__isnull=True,
            )
            .exclude(
                stage__in=[
                    Opportunity.Stage.PRICING,
                    Opportunity.Stage.SUBMITTED,
                    Opportunity.Stage.WON,
                    Opportunity.Stage.LOST,
                ]
            )
            .order_by("id")
            .first()
        )
        if candidate is not None:
            return candidate

        # Fall back: create a fresh throwaway opportunity populated
        # with every field the mapping reads.
        company = Company.objects.first()
        if company is None:
            raise RuntimeError(
                "No Company exists; run `python manage.py seed_demo` first."
            )
        from time import time

        return Opportunity.objects.create(
            project_name="Quote Mapping Proof",
            project_code=f"PROOF-{int(time())}",
            company=company,
            stage=Opportunity.Stage.LEAD,
            estimated_contract_value=Decimal("640000.00"),
            estimated_margin_percent=Decimal("12.50"),
            submission_date="2026-05-15",
        )

    # ------------------------------------------------------------------
    # API drive
    # ------------------------------------------------------------------
    @staticmethod
    def _patch_stage_submitted(opp_id: int, actor: AppUser):
        factory = APIRequestFactory()
        request = factory.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        force_authenticate(request, user=actor)
        view = OpportunityViewSet.as_view({"patch": "partial_update"})
        return view(request, pk=opp_id)

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------
    def _print_source_fields(self, opp: Opportunity) -> None:
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("SOURCE — opportunity fields before patch")
        self.stdout.write("=" * 60)
        for field in (
            "id",
            "project_code",
            "project_name",
            "stage",
            "estimated_contract_value",
            "estimated_margin_percent",
            "submission_date",
        ):
            self.stdout.write(f"  {field:<26} = {getattr(opp, field)!r}")

    def _print_quote_fields(self, q: Quote) -> None:
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("QUOTE — fields on the created row")
        self.stdout.write("=" * 60)
        for field in (
            "id",
            "opportunity_id",
            "revision_number",
            "quote_reference",
            "quoted_value_ex_gst",
            "quoted_margin_percent",
            "submission_date",
            "quote_status",
            "created_at",
        ):
            self.stdout.write(f"  {field:<26} = {getattr(q, field)!r}")

    def _print_mapping_assertions(
        self, opp: Opportunity, q: Quote
    ) -> None:
        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("MAPPING — Opportunity → Quote assertions")
        self.stdout.write("=" * 60)

        expected_ref = f"{opp.project_code}-R{q.revision_number}"
        checks = [
            (
                "Opportunity.estimated_contract_value → Quote.quoted_value_ex_gst",
                opp.estimated_contract_value,
                q.quoted_value_ex_gst,
            ),
            (
                "Opportunity.estimated_margin_percent → Quote.quoted_margin_percent",
                opp.estimated_margin_percent,
                q.quoted_margin_percent,
            ),
            (
                "Opportunity.submission_date → Quote.submission_date",
                opp.submission_date,
                q.submission_date,
            ),
            (
                "Opportunity.project_code → Quote.quote_reference (+ '-R{n}')",
                expected_ref,
                q.quote_reference,
            ),
        ]

        all_pass = True
        for label, expected, actual in checks:
            ok = expected == actual
            tag = self.style.SUCCESS("PASS") if ok else self.style.ERROR("FAIL")
            self.stdout.write(f"  {tag}  {label}")
            self.stdout.write(f"        expected: {expected!r}")
            self.stdout.write(f"        actual:   {actual!r}")
            if not ok:
                all_pass = False

        self.stdout.write("")
        if all_pass:
            self.stdout.write(self.style.SUCCESS(
                "PROOF: every mapping matched the expected opportunity field."
            ))
        else:
            self.stdout.write(self.style.ERROR(
                "PROOF NEGATIVE: at least one field did not map as expected."
            ))

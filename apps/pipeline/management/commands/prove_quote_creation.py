"""
One-shot proof test: drive a real opportunity stage transition through
the same DRF view code path the API uses, and show that a Quote record
appears as a side effect.

Usage:
    python manage.py prove_quote_creation

Picks an existing Opportunity with a positive estimated_contract_value
and no quote yet. If none qualifies (e.g. every eligible opp has been
quoted already by previous runs), creates a temporary one. PATCHes
stage to "submitted" via OpportunityViewSet — the same code path the
React frontend hits — then prints the quote count delta and the new
quote's fields.

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
        "Drive a real opportunity through OpportunityViewSet to prove "
        "that auto-quote-creation fires on the actual write path."
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

        opp = self._pick_or_create_opportunity()
        before = opp.quotes.count()

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("BEFORE")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  opportunity.id           = {opp.id}")
        self.stdout.write(f"  opportunity.project_code = {opp.project_code}")
        self.stdout.write(f"  opportunity.project_name = {opp.project_name}")
        self.stdout.write(f"  opportunity.stage        = {opp.stage}")
        self.stdout.write(
            f"  opportunity.estimated_contract_value = "
            f"{opp.estimated_contract_value}"
        )
        self.stdout.write(f"  Quote count for opportunity: {before}")

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write(
            'PATCH /api/opportunities/{id}/  with {"stage": "submitted"}'
        )
        self.stdout.write("(driven through OpportunityViewSet — same path the API uses)")
        self.stdout.write("=" * 60)
        response = self._patch_stage_submitted(opp.id, actor)
        self.stdout.write(f"  HTTP status: {response.status_code}")
        if response.status_code >= 400:
            self.stdout.write(self.style.ERROR(
                f"  Response: {response.data}"
            ))
            return

        opp.refresh_from_db()
        after = opp.quotes.count()

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("AFTER")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  opportunity.stage  = {opp.stage}")
        self.stdout.write(f"  opportunity.status = {opp.status}")
        self.stdout.write(f"  Quote count for opportunity: {after}")
        self.stdout.write(f"  Delta: +{after - before}")

        new_quote = (
            Quote.objects.filter(opportunity=opp).order_by("-revision_number").first()
        )
        if new_quote is None:
            self.stdout.write(self.style.WARNING(
                "  No quote found after the patch — auto-creation did NOT fire."
            ))
            return

        self.stdout.write("")
        self.stdout.write("=" * 60)
        self.stdout.write("CREATED QUOTE")
        self.stdout.write("=" * 60)
        for field in (
            "id",
            "revision_number",
            "quote_reference",
            "quoted_value_ex_gst",
            "quote_status",
            "submission_date",
            "created_at",
        ):
            self.stdout.write(f"  {field:<22} = {getattr(new_quote, field)!r}")

        if after > before:
            self.stdout.write("")
            self.stdout.write(self.style.SUCCESS(
                "PROOF: auto-quote-creation fired on the real API path."
            ))
        else:
            self.stdout.write("")
            self.stdout.write(self.style.WARNING(
                "PROOF NEGATIVE: Quote count did not increase. Check server "
                "logs for `quote_automation:` lines."
            ))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _pick_or_create_opportunity() -> Opportunity:
        # Prefer an existing opportunity that already has a value but no
        # quote and is in a non-eligible stage — that maximises the
        # signal (count goes 0 → 1).
        opp = (
            Opportunity.objects.filter(
                estimated_contract_value__gt=0,
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
        if opp is not None:
            return opp

        # Fall back: create a fresh throwaway opportunity for the proof.
        company = Company.objects.first()
        if company is None:
            raise RuntimeError(
                "No Company exists; run `python manage.py seed_demo` first."
            )
        from time import time

        return Opportunity.objects.create(
            project_name="Quote Auto-Create Proof",
            project_code=f"PROOF-{int(time())}",
            company=company,
            stage=Opportunity.Stage.LEAD,
            estimated_contract_value=Decimal("500000.00"),
        )

    @staticmethod
    def _patch_stage_submitted(opp_id: int, actor: AppUser):
        # Use the DRF view as the entry point so every middleware-equivalent
        # behaviour (perform_update, activity logging, quote_automation)
        # runs exactly as it does for a real API request. Auth is bypassed
        # via force_authenticate — appropriate for a debug command.
        factory = APIRequestFactory()
        request = factory.patch(
            f"/api/opportunities/{opp_id}/",
            {"stage": Opportunity.Stage.SUBMITTED},
            format="json",
        )
        force_authenticate(request, user=actor)
        view = OpportunityViewSet.as_view({"patch": "partial_update"})
        return view(request, pk=opp_id)

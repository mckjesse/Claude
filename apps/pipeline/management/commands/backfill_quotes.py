"""
One-shot backfill of Quote records for opportunities that were created
or transitioned into an eligible stage *before* the quote-auto-create
service was deployed.

For every Opportunity that:
  - has stage in {pricing, submitted, won, lost}
  - has a quoting value > 0
  - has zero existing Quote rows
the command creates a rev-1 Quote using the same code path as the
runtime trigger (sync_quote_from_opportunity), so the result is
identical to what would have happened if the trigger had been live
when the opportunity was written.

Usage:
    python manage.py backfill_quotes              # write the rows
    python manage.py backfill_quotes --dry-run    # report only

Idempotent — re-running after a successful run produces no new rows
because each affected opportunity now has a Quote.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.pipeline.models import Opportunity
from apps.pipeline.services import quote_automation


class Command(BaseCommand):
    help = (
        "Create rev-1 Quote records for any opportunity that meets the "
        "quote-auto-create rule but has no Quote yet."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report which opportunities would get a quote, but do not write.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        candidates = (
            Opportunity.objects
            .filter(stage__in=quote_automation._ELIGIBLE_STAGES)
            .annotate(quote_count=Count("quotes"))
            .filter(quote_count=0)
            .order_by("id")
        )

        considered = candidates.count()
        self.stdout.write(
            f"Considering {considered} opportunities with no quote and "
            f"eligible stage."
        )

        created = 0
        skipped = 0
        for opp in candidates:
            value = quote_automation._value_for_quote(opp)
            if value is None or value <= 0:
                skipped += 1
                self.stdout.write(
                    f"  skip opp={opp.pk} ({opp.project_code}) — "
                    f"no positive value"
                )
                continue
            if dry_run:
                self.stdout.write(
                    f"  would create rev=1 opp={opp.pk} "
                    f"({opp.project_code}) value={value} stage={opp.stage}"
                )
                created += 1
                continue
            quote = quote_automation.sync_quote_from_opportunity(opp, user=None)
            if quote is not None:
                created += 1
                self.stdout.write(
                    f"  wrote Quote(id={quote.id}, rev={quote.revision_number}, "
                    f"value={quote.quoted_value_ex_gst}) for opp={opp.pk}"
                )
            else:
                skipped += 1

        verb = "would create" if dry_run else "created"
        self.stdout.write(
            self.style.SUCCESS(
                f"\nDone. {verb} {created} quote(s); skipped {skipped}."
            )
        )

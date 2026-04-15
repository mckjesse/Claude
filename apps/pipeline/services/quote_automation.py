"""
Automatic Quote creation driven by Opportunity workflow.

Business rule:
- When an Opportunity enters stage "pricing" or "submitted" and has a
  value, keep a Quote record in sync with the opportunity.
- First time an eligible opportunity reaches these stages:
  create revision 1.
- Subsequent times:
  only create a new revision when the quote value changes or when the
  opportunity transitions INTO "submitted" from another stage
  (a resubmission event).
- Ordinary edits that change neither the value nor the eligible stage
  do not create duplicates.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional

from apps.users.models import AppUser

from ..models import Opportunity, Quote
from . import activity

_ELIGIBLE_STAGES: set[str] = {
    Opportunity.Stage.PRICING,
    Opportunity.Stage.SUBMITTED,
}


def sync_quote_from_opportunity(
    opportunity: Opportunity,
    *,
    user: Optional[AppUser] = None,
    old_stage: Optional[str] = None,
    old_value: Optional[Decimal] = None,
) -> Optional[Quote]:
    """
    Ensure the Quote list for ``opportunity`` reflects the current
    pricing workflow. Returns the newly created Quote if one was
    created, else None.

    Callers pass ``old_stage`` and ``old_value`` (the values before
    ``opportunity`` was saved) so we can detect resubmission and
    material value changes without doing our own pre-save snapshot.
    """
    if opportunity.stage not in _ELIGIBLE_STAGES:
        return None
    if opportunity.estimated_contract_value is None:
        return None

    latest = (
        opportunity.quotes.order_by("-revision_number").first()
    )

    # First quote for this opportunity.
    if latest is None:
        return _create_quote(opportunity, revision=1, user=user)

    value_changed = (
        opportunity.estimated_contract_value != latest.quoted_value_ex_gst
    )
    transitioned_into_submitted = (
        opportunity.stage == Opportunity.Stage.SUBMITTED
        and old_stage != Opportunity.Stage.SUBMITTED
    )
    if value_changed or transitioned_into_submitted:
        return _create_quote(
            opportunity,
            revision=latest.revision_number + 1,
            user=user,
        )

    return None


def _create_quote(
    opp: Opportunity,
    *,
    revision: int,
    user: Optional[AppUser],
) -> Quote:
    is_submitted_stage = opp.stage == Opportunity.Stage.SUBMITTED
    quote = Quote.objects.create(
        opportunity=opp,
        revision_number=revision,
        quoted_value_ex_gst=opp.estimated_contract_value,
        quote_reference=f"{opp.project_code}-R{revision}",
        quote_status=(
            Quote.QuoteStatus.SUBMITTED
            if is_submitted_stage
            else Quote.QuoteStatus.DRAFT
        ),
        submission_date=(
            opp.submission_date if is_submitted_stage else None
        ),
    )
    # Keep the opportunity's activity feed consistent with manual quote
    # creation. Doing it here (not via QuoteViewSet.perform_create) is
    # correct because the service is the single creation path.
    activity.quote_created(quote, user)
    return quote

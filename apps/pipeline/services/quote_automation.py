"""
Automatic Quote creation driven by Opportunity workflow.

Business rule:
- An opportunity whose stage is one of {pricing, submitted, won, lost}
  and whose quoting value is > 0 always has at least one Quote.
  * First time: revision 1.
  * Subsequent times: a new revision only when the quoting value
    differs from the latest quote. Unrelated edits never create a
    duplicate.

Value source:
- For won opportunities the authoritative amount is ``final_awarded_value``.
- For every other eligible stage it is ``estimated_contract_value``.
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
    Opportunity.Stage.WON,
    Opportunity.Stage.LOST,
}

_STATUS_FOR_STAGE: dict[str, str] = {
    Opportunity.Stage.PRICING: Quote.QuoteStatus.DRAFT,
    Opportunity.Stage.SUBMITTED: Quote.QuoteStatus.SUBMITTED,
    Opportunity.Stage.WON: Quote.QuoteStatus.ACCEPTED,
    Opportunity.Stage.LOST: Quote.QuoteStatus.UNSUCCESSFUL,
}


def sync_quote_from_opportunity(
    opportunity: Opportunity,
    *,
    user: Optional[AppUser] = None,
) -> Optional[Quote]:
    """
    Ensure the Quote list for ``opportunity`` reflects its current
    pricing state. Returns the newly created Quote if one was written,
    else ``None``.

    Idempotent — safe to call from any save path. On ordinary edits
    that change neither the stage (into an eligible one) nor the
    quoting value, this is a no-op.
    """
    if opportunity.stage not in _ELIGIBLE_STAGES:
        return None

    value = _value_for_quote(opportunity)
    if value is None or value <= 0:
        return None

    latest = opportunity.quotes.order_by("-revision_number").first()

    # First quote.
    if latest is None:
        return _create_quote(opportunity, revision=1, value=value, user=user)

    # Only create a new revision when the quoting value has materially
    # changed. Strict Decimal equality — deliberate; "materially" is
    # whatever the user-facing value is.
    if value != latest.quoted_value_ex_gst:
        return _create_quote(
            opportunity,
            revision=latest.revision_number + 1,
            value=value,
            user=user,
        )

    return None


def _value_for_quote(opp: Opportunity) -> Optional[Decimal]:
    if opp.stage == Opportunity.Stage.WON and opp.final_awarded_value is not None:
        return opp.final_awarded_value
    return opp.estimated_contract_value


def _create_quote(
    opp: Opportunity,
    *,
    revision: int,
    value: Decimal,
    user: Optional[AppUser],
) -> Quote:
    quote_status = _STATUS_FOR_STAGE.get(opp.stage, Quote.QuoteStatus.DRAFT)
    quote = Quote.objects.create(
        opportunity=opp,
        revision_number=revision,
        quoted_value_ex_gst=value,
        quote_reference=f"{opp.project_code}-R{revision}",
        quote_status=quote_status,
        submission_date=(
            opp.submission_date
            if opp.stage == Opportunity.Stage.SUBMITTED
            else None
        ),
    )
    # Keep the opportunity's activity feed consistent with manual quote
    # creation. Safe even when user is None (an unauthenticated path
    # would never reach here, but the helper tolerates it anyway).
    activity.quote_created(quote, user)
    return quote

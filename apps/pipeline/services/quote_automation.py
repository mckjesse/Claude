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

Logging: this module logs at INFO on every call so production
deployments can prove the trigger fired and see the decision branch
taken. Greppable prefix: ``quote_automation``.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from apps.users.models import AppUser

from ..models import Opportunity, Quote
from . import activity

logger = logging.getLogger(__name__)

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
    """
    pk = opportunity.pk
    stage = opportunity.stage

    if stage not in _ELIGIBLE_STAGES:
        logger.info(
            "quote_automation: skip opp=%s stage=%s reason=ineligible_stage",
            pk, stage,
        )
        return None

    value = _value_for_quote(opportunity)
    if value is None or value <= 0:
        logger.info(
            "quote_automation: skip opp=%s stage=%s reason=value_missing_or_zero value=%r",
            pk, stage, value,
        )
        return None

    latest = opportunity.quotes.order_by("-revision_number").first()

    if latest is None:
        logger.info(
            "quote_automation: creating rev=1 opp=%s stage=%s value=%s",
            pk, stage, value,
        )
        return _create_quote(opportunity, revision=1, value=value, user=user)

    if value != latest.quoted_value_ex_gst:
        new_rev = latest.revision_number + 1
        logger.info(
            "quote_automation: creating rev=%s opp=%s stage=%s "
            "old_value=%s new_value=%s",
            new_rev, pk, stage, latest.quoted_value_ex_gst, value,
        )
        return _create_quote(
            opportunity, revision=new_rev, value=value, user=user
        )

    logger.info(
        "quote_automation: skip opp=%s stage=%s reason=value_unchanged value=%s "
        "latest_rev=%s",
        pk, stage, value, latest.revision_number,
    )
    return None


def _value_for_quote(opp: Opportunity) -> Optional[Decimal]:
    if opp.stage == Opportunity.Stage.WON and opp.final_awarded_value is not None:
        return opp.final_awarded_value
    return opp.estimated_contract_value


def _build_quote_payload(
    opp: Opportunity,
    *,
    revision: int,
    value: Decimal,
) -> dict:
    """
    Explicit field mapping from Opportunity → Quote.

    ┌──────────────────────────────────────── Opportunity ─ → ─ Quote ──────────┐
    │  opp                                 → opportunity (FK id)                │
    │  opp.project_code + "-R{revision}"   → quote_reference                    │
    │  value (_value_for_quote)            → quoted_value_ex_gst                │
    │  opp.estimated_margin_percent        → quoted_margin_percent              │
    │  opp.submission_date                 → submission_date                    │
    │  _STATUS_FOR_STAGE[opp.stage]        → quote_status                       │
    │  (constant)                          → revision_number = revision         │
    └──────────────────────────────────────────────────────────────────────────┘

    Keeping the mapping in one dedicated function makes it obvious
    which source field feeds which destination field — no serializer
    magic, no signals, no implicit defaults hidden in the model.
    """
    return {
        "opportunity": opp,
        "revision_number": revision,
        "quote_reference": f"{opp.project_code}-R{revision}",
        "quoted_value_ex_gst": value,
        "quoted_margin_percent": opp.estimated_margin_percent,
        "submission_date": opp.submission_date,
        "quote_status": _STATUS_FOR_STAGE.get(
            opp.stage, Quote.QuoteStatus.DRAFT
        ),
    }


def _create_quote(
    opp: Opportunity,
    *,
    revision: int,
    value: Decimal,
    user: Optional[AppUser],
) -> Quote:
    payload = _build_quote_payload(opp, revision=revision, value=value)
    quote = Quote.objects.create(**payload)
    activity.quote_created(quote, user)
    logger.info(
        "quote_automation: wrote Quote(id=%s, opp=%s, rev=%s, value=%s, status=%s)",
        quote.id, opp.pk, quote.revision_number, value, payload["quote_status"],
    )
    return quote


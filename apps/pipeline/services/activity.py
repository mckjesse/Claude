"""
Activity log writer.

Centralises the creation of ``ActivityLog`` entries so each viewset can
emit business-level events with one call per event. Descriptions are
kept in plain business language — they surface in the opportunity
activity feed and are read by non-technical users.

This module is driven from the DRF viewset lifecycle (``perform_create``,
``perform_update``, custom actions) rather than from Django model
signals. Signals would cover the admin site and management shell too,
but they cannot see the acting user without thread-locals. The frontend
uses the DRF API, so the DRF hooks give full coverage for real traffic.
Changes made in the Django admin or ``manage.py shell`` will not
produce activity entries — that is intentional.
"""
from __future__ import annotations

from typing import Iterable, Optional

from apps.users.models import AppUser

from ..models import ActivityLog, FollowUpTask, LossReason, Opportunity, Quote

# ---------------------------------------------------------------------------
# Curated field sets — only these fields are watched for the generic
# "updated" events. Add fields here as they become business-relevant.
# ---------------------------------------------------------------------------
OPPORTUNITY_TRACKED_FIELDS = (
    "project_name",
    "project_code",
    "status",
    "company_id",
    "primary_contact_id",
    "estimator_id",
    "assigned_user_id",
    "estimated_contract_value",
    "estimated_margin_percent",
    "probability_percent",
    "final_awarded_value",
    "submission_due_date",
    "submission_date",
    "expected_award_date",
    "scope_summary",
    "inclusions_summary",
    "exclusions_summary",
    "notes",
    "sector",
    "tender_type",
    "opportunity_source",
    "site_suburb",
)

QUOTE_TRACKED_FIELDS = (
    "quote_reference",
    "quoted_value_ex_gst",
    "quoted_margin_percent",
    "discount_percent",
    "submission_date",
    "validity_date",
    "quote_status",
)

FOLLOWUP_TRACKED_FIELDS = (
    "subject",
    "details",
    "assigned_to_user_id",
    "task_type",
    "due_date",
    "due_time",
    "priority",
    "status",
    "related_quote_id",
)

# ---------------------------------------------------------------------------
# Human-friendly field labels used in activity descriptions.
# ---------------------------------------------------------------------------
FIELD_LABELS: dict[str, str] = {
    # Opportunity
    "project_name": "project name",
    "project_code": "project code",
    "status": "status",
    "company_id": "company",
    "primary_contact_id": "primary contact",
    "estimator_id": "estimator",
    "assigned_user_id": "assigned user",
    "estimated_contract_value": "estimated contract value",
    "estimated_margin_percent": "estimated margin",
    "probability_percent": "probability",
    "final_awarded_value": "final awarded value",
    "submission_due_date": "submission due date",
    "submission_date": "submission date",
    "expected_award_date": "expected award date",
    "scope_summary": "scope summary",
    "inclusions_summary": "inclusions",
    "exclusions_summary": "exclusions",
    "notes": "notes",
    "sector": "sector",
    "tender_type": "tender type",
    "opportunity_source": "opportunity source",
    "site_suburb": "site suburb",
    # Quote
    "quote_reference": "quote reference",
    "quoted_value_ex_gst": "quoted value",
    "quoted_margin_percent": "quoted margin",
    "discount_percent": "discount",
    "validity_date": "validity date",
    "quote_status": "quote status",
    # Follow-up
    "subject": "subject",
    "details": "details",
    "assigned_to_user_id": "assigned user",
    "task_type": "task type",
    "due_date": "due date",
    "due_time": "due time",
    "priority": "priority",
    "related_quote_id": "related quote",
}


def _humanise(fields: Iterable[str]) -> str:
    labels = [FIELD_LABELS.get(f, f.replace("_", " ")) for f in fields]
    if not labels:
        return ""
    if len(labels) == 1:
        return labels[0]
    if len(labels) == 2:
        return f"{labels[0]} and {labels[1]}"
    return ", ".join(labels[:-1]) + f", and {labels[-1]}"


def _stage_label(value: str) -> str:
    if not value:
        return "unspecified"
    try:
        return Opportunity.Stage(value).label
    except ValueError:
        return value


def _loss_reason_label(value: str) -> str:
    if not value:
        return "unspecified"
    try:
        return LossReason.Category(value).label
    except ValueError:
        return value


# ---------------------------------------------------------------------------
# Snapshot + diff helpers
# ---------------------------------------------------------------------------
def snapshot(instance, fields: Iterable[str]) -> dict:
    """Capture the current values of ``fields`` on ``instance``."""
    return {f: getattr(instance, f) for f in fields}


def diff(instance, baseline: dict) -> list[str]:
    """Return the subset of ``baseline`` keys whose values differ now."""
    return [f for f, v in baseline.items() if getattr(instance, f) != v]


# ---------------------------------------------------------------------------
# Low-level writer
# ---------------------------------------------------------------------------
def _log(
    *,
    opportunity: Opportunity,
    entity_type: str,
    entity_id: int | None,
    activity_type: str,
    description: str,
    user: Optional[AppUser] = None,
) -> ActivityLog:
    return ActivityLog.objects.create(
        opportunity=opportunity,
        entity_type=entity_type,
        entity_id=entity_id,
        activity_type=activity_type,
        description=description,
        created_by_user=(
            user if user and user.is_authenticated else None
        ),
    )


# ---------------------------------------------------------------------------
# Opportunity events
# ---------------------------------------------------------------------------
def opportunity_created(opp: Opportunity, user) -> None:
    _log(
        opportunity=opp,
        entity_type="opportunity",
        entity_id=opp.id,
        activity_type="opportunity_created",
        description=f"Opportunity created: {opp.project_name}.",
        user=user,
    )


def opportunity_updated(opp: Opportunity, user, changed_fields: list[str]) -> None:
    # Stage changes have their own dedicated event; strip them from the
    # generic description so we never log both for the same save.
    changed = [f for f in changed_fields if f != "stage"]
    if not changed:
        return
    _log(
        opportunity=opp,
        entity_type="opportunity",
        entity_id=opp.id,
        activity_type="opportunity_updated",
        description=f"Opportunity details updated: {_humanise(changed)}.",
        user=user,
    )


def opportunity_stage_changed(
    opp: Opportunity, user, old_stage: str, new_stage: str
) -> None:
    _log(
        opportunity=opp,
        entity_type="opportunity",
        entity_id=opp.id,
        activity_type="stage_changed",
        description=(
            f"Stage changed from {_stage_label(old_stage)} to "
            f"{_stage_label(new_stage)}."
        ),
        user=user,
    )


def opportunity_marked_won(opp: Opportunity, user, final_value) -> None:
    _log(
        opportunity=opp,
        entity_type="opportunity",
        entity_id=opp.id,
        activity_type="marked_won",
        description=(
            f"Opportunity marked won at ${final_value}."
            if final_value is not None
            else "Opportunity marked won."
        ),
        user=user,
    )


def opportunity_marked_lost(
    opp: Opportunity, user, reason_category: str, competitor_name: str = ""
) -> None:
    tail = f" (competitor: {competitor_name})" if competitor_name else ""
    _log(
        opportunity=opp,
        entity_type="opportunity",
        entity_id=opp.id,
        activity_type="marked_lost",
        description=(
            f"Opportunity marked lost — reason: "
            f"{_loss_reason_label(reason_category)}{tail}."
        ),
        user=user,
    )


# ---------------------------------------------------------------------------
# Quote events
# ---------------------------------------------------------------------------
def quote_created(quote: Quote, user) -> None:
    ref = f" ({quote.quote_reference})" if quote.quote_reference else ""
    _log(
        opportunity=quote.opportunity,
        entity_type="quote",
        entity_id=quote.id,
        activity_type="quote_created",
        description=f"Quote rev {quote.revision_number} created{ref}.",
        user=user,
    )


def quote_updated(quote: Quote, user, changed_fields: list[str]) -> None:
    if not changed_fields:
        return
    _log(
        opportunity=quote.opportunity,
        entity_type="quote",
        entity_id=quote.id,
        activity_type="quote_updated",
        description=(
            f"Quote rev {quote.revision_number} updated: "
            f"{_humanise(changed_fields)}."
        ),
        user=user,
    )


# ---------------------------------------------------------------------------
# Follow-up events
# ---------------------------------------------------------------------------
def followup_created(task: FollowUpTask, user) -> None:
    _log(
        opportunity=task.opportunity,
        entity_type="followup",
        entity_id=task.id,
        activity_type="followup_created",
        description=f"Follow-up task created: {task.subject}.",
        user=user,
    )


def followup_updated(task: FollowUpTask, user, changed_fields: list[str]) -> None:
    # Completion has its own event.
    changed = [f for f in changed_fields if f != "status"]
    if not changed:
        return
    _log(
        opportunity=task.opportunity,
        entity_type="followup",
        entity_id=task.id,
        activity_type="followup_updated",
        description=(
            f"Follow-up '{task.subject}' updated: {_humanise(changed)}."
        ),
        user=user,
    )


def opportunity_archived(opp: Opportunity, user) -> None:
    _log(
        opportunity=opp,
        entity_type="opportunity",
        entity_id=opp.id,
        activity_type="archived",
        description=f"Opportunity archived: {opp.project_name}.",
        user=user,
    )


def opportunity_restored(opp: Opportunity, user) -> None:
    _log(
        opportunity=opp,
        entity_type="opportunity",
        entity_id=opp.id,
        activity_type="restored",
        description=f"Opportunity restored: {opp.project_name}.",
        user=user,
    )


def followup_completed(task: FollowUpTask, user) -> None:
    _log(
        opportunity=task.opportunity,
        entity_type="followup",
        entity_id=task.id,
        activity_type="followup_completed",
        description=f"Follow-up '{task.subject}' marked completed.",
        user=user,
    )

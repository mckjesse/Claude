"""
Automatic follow-up creation on opportunity stage transitions.

When an Opportunity enters stage "submitted", a follow-up task is
created 14 days after the submission date so the estimator (or whoever
is assigned) gets a reminder to chase the client.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from apps.users.models import AppUser

from ..models import FollowUpTask, Opportunity
from . import activity

logger = logging.getLogger(__name__)

_SUBJECT = "Follow up on submitted quote"

_AUTO_CANCEL_NOTE = (
    "Automatically closed because opportunity was marked as {reason}."
)


def clear_followups_for_terminal_opportunity(
    opportunity: Opportunity,
    *,
    user: Optional[AppUser] = None,
    reason: str = "closed",
) -> list[int]:
    """
    Cancel every outstanding follow-up for an opportunity that has just
    become terminal (won / lost / closed).

    "Outstanding" means ``status = PENDING`` and ``completed_at IS NULL``.
    Matching tasks are moved to ``CANCELLED`` — never hard-deleted — with
    a completion note, timestamp and (if available) the acting user, so
    the history is preserved. Idempotent: once cleared, a repeat call
    finds nothing.

    Returns the list of cleared follow-up ids.
    """
    pending = list(
        opportunity.tasks.filter(
            status=FollowUpTask.Status.PENDING,
            completed_at__isnull=True,
        )
    )

    # Requirement 7: debug/admin logging of what was found.
    logger.info(
        "followup_clear: opp=%s terminal_stage=%s pending_found=%s",
        opportunity.pk,
        reason,
        len(pending),
    )
    if not pending:
        return []

    now = timezone.now()
    note = _AUTO_CANCEL_NOTE.format(reason=reason)
    acting_user = (
        user if (user is not None and getattr(user, "is_authenticated", False))
        else None
    )

    cleared_ids: list[int] = []
    for task in pending:
        task.status = FollowUpTask.Status.CANCELLED
        task.completed_at = now
        task.completion_notes = note
        task.completed_by = acting_user
        task.save(
            update_fields=[
                "status",
                "completed_at",
                "completion_notes",
                "completed_by",
                "updated_at",
            ]
        )
        activity.followup_auto_cancelled(task, user, reason)
        cleared_ids.append(task.id)

    logger.info(
        "followup_clear: opp=%s terminal_stage=%s cleared_count=%s "
        "cleared_ids=%s",
        opportunity.pk,
        reason,
        len(cleared_ids),
        cleared_ids,
    )
    return cleared_ids


def sync_followup_from_opportunity(
    opportunity: Opportunity,
    *,
    user: Optional[AppUser] = None,
    old_stage: Optional[str] = None,
) -> Optional[FollowUpTask]:
    """
    If the opportunity just transitioned into "submitted", create a
    pending follow-up task due 14 days after submission_date.

    Returns the new FollowUpTask if one was created, else None.
    Idempotent — a second call for the same opportunity produces nothing
    if the canonical follow-up already exists.
    """
    # Only fire on transition INTO submitted.
    if opportunity.stage != Opportunity.Stage.SUBMITTED:
        return None
    if old_stage == Opportunity.Stage.SUBMITTED:
        return None

    # Duplicate guard: check for an existing auto-generated follow-up
    # for this opportunity with the canonical subject.
    already_exists = FollowUpTask.objects.filter(
        opportunity=opportunity,
        subject=_SUBJECT,
    ).exists()
    if already_exists:
        logger.info(
            "followup_automation: skip opp=%s reason=already_exists",
            opportunity.pk,
        )
        return None

    base_date = opportunity.submission_date or timezone.localdate()
    due_date = base_date + timedelta(days=14)

    assignee = (
        opportunity.assigned_user
        or opportunity.estimator
        or user
    )
    if assignee is None:
        logger.warning(
            "followup_automation: skip opp=%s reason=no_assignee",
            opportunity.pk,
        )
        return None

    task = FollowUpTask.objects.create(
        opportunity=opportunity,
        assigned_to_user=assignee,
        subject=_SUBJECT,
        task_type=FollowUpTask.TaskType.EMAIL,
        status=FollowUpTask.Status.PENDING,
        priority=FollowUpTask.Priority.MEDIUM,
        due_date=due_date,
        details=(
            f"Opportunity '{opportunity.project_name}' was submitted. "
            f"Follow up with {opportunity.company.name if opportunity.company_id else 'the client'}."
        ),
    )
    activity.followup_created(task, user)
    logger.info(
        "followup_automation: created task=%s opp=%s due=%s assignee=%s",
        task.pk, opportunity.pk, due_date, assignee.username,
    )
    return task

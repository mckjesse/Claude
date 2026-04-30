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

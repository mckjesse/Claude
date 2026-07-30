"""
Dashboard aggregation service.

All queries are funnelled through ``scoping`` so role-based access can
be layered on later without touching this module.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.users.models import AppUser

from ..models import FollowUpTask, Opportunity, Quote
from . import scoping

ZERO_DEC = Decimal("0.00")
_VALUE_SUM = Coalesce(
    Sum("estimated_contract_value"),
    ZERO_DEC,
    output_field=DecimalField(max_digits=16, decimal_places=2),
)

_RECENT_ACTIVITY_LIMIT = 10
_TOP_OVERDUE_LIMIT = 5


def build_dashboard(user: AppUser) -> dict:
    today = timezone.localdate()
    horizon = today + timedelta(days=7)

    opps = scoping.scoped_opportunities(user)
    tasks = scoping.scoped_followups(user)
    quotes = scoping.scoped_quotes(user)
    activity = scoping.scoped_activity(user)

    open_opps = opps.filter(status=Opportunity.Status.OPEN)
    # Pending dashboard follow-ups exclude anything already completed or
    # cancelled, AND anything whose parent opportunity is terminal
    # (won / lost / closed) — a follow-up on a closed opportunity must
    # never surface as outstanding, even if it somehow stayed pending.
    active_tasks = (
        tasks.exclude(
            status__in=[
                FollowUpTask.Status.COMPLETED,
                FollowUpTask.Status.CANCELLED,
            ]
        )
        .exclude(
            opportunity__stage__in=[
                Opportunity.Stage.WON,
                Opportunity.Stage.LOST,
            ]
        )
        .exclude(opportunity__status=Opportunity.Status.CLOSED)
    )

    totals = open_opps.aggregate(total=_VALUE_SUM)

    return {
        "total_open_pipeline_value": totals["total"],
        "active_opportunities": open_opps.count(),
        "quotes_awaiting_follow_up": quotes.filter(
            quote_status=Quote.QuoteStatus.SUBMITTED,
            opportunity__status=Opportunity.Status.OPEN,
        ).count(),
        "overdue_followups": active_tasks.filter(due_date__lt=today).count(),
        "followups_due_today": active_tasks.filter(due_date=today).count(),
        "upcoming_submissions_7_days": open_opps.filter(
            submission_due_date__gte=today,
            submission_due_date__lte=horizon,
        ).count(),
        "opportunities_by_stage": _opportunities_by_stage(open_opps),
        "recent_activity": _recent_activity(activity),
        "top_overdue_followups": _top_overdue_followups(active_tasks, today),
    }


def _opportunities_by_stage(open_opps) -> list[dict]:
    rows = {
        row["stage"]: row
        for row in open_opps.values("stage").annotate(
            count=Count("id"),
            value=_VALUE_SUM,
        )
    }
    return [
        {
            "stage": stage.value,
            "stage_label": stage.label,
            "count": rows.get(stage.value, {}).get("count", 0),
            "value": rows.get(stage.value, {}).get("value", ZERO_DEC),
        }
        for stage in Opportunity.Stage
    ]


def _recent_activity(activity_qs) -> list[dict]:
    logs = activity_qs.select_related("created_by_user", "opportunity")[
        :_RECENT_ACTIVITY_LIMIT
    ]
    return [
        {
            "id": a.id,
            "activity_type": a.activity_type,
            "entity_type": a.entity_type,
            "entity_id": a.entity_id,
            "description": a.description,
            "created_at": a.created_at,
            "opportunity": {
                "id": a.opportunity_id,
                "project_name": a.opportunity.project_name,
            },
            "created_by_user": (
                {
                    "id": a.created_by_user_id,
                    "username": a.created_by_user.username,
                    "display_name": a.created_by_user.display_name,
                }
                if a.created_by_user_id
                else None
            ),
        }
        for a in logs
    ]


def _top_overdue_followups(active_tasks, today) -> list[dict]:
    tasks = (
        active_tasks.filter(due_date__lt=today)
        .select_related("opportunity", "opportunity__company", "assigned_to_user")
        .order_by("due_date", "-priority")[:_TOP_OVERDUE_LIMIT]
    )
    return [
        {
            "id": t.id,
            "subject": t.subject,
            "due_date": t.due_date,
            "days_overdue": (today - t.due_date).days,
            "priority": t.priority,
            "status": t.status,
            "task_type": t.task_type,
            "opportunity": {
                "id": t.opportunity_id,
                "project_name": t.opportunity.project_name,
                "company_name": (
                    t.opportunity.company.name if t.opportunity.company_id else None
                ),
            },
            "assigned_to_user": {
                "id": t.assigned_to_user_id,
                "username": t.assigned_to_user.username,
                "display_name": t.assigned_to_user.display_name,
            },
        }
        for t in tasks
    ]

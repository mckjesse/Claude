"""
Reporting service.

Each function returns a plain list/dict ready to be JSON-serialised by
DRF. Keep query logic readable over clever — we would rather add more
functions than build a generic reporting framework.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, DecimalField, Max, Q, Sum
from django.db.models.functions import Coalesce
from django.utils import timezone

from apps.users.models import AppUser

from ..models import FollowUpTask, LossReason, Opportunity
from . import scoping

ZERO_DEC = Decimal("0.00")

_ESTIMATED_SUM = Coalesce(
    Sum("estimated_contract_value"),
    ZERO_DEC,
    output_field=DecimalField(max_digits=16, decimal_places=2),
)


def _won_value_sum():
    return Coalesce(
        Sum("final_awarded_value", filter=Q(stage=Opportunity.Stage.WON)),
        ZERO_DEC,
        output_field=DecimalField(max_digits=16, decimal_places=2),
    )


# ---------------------------------------------------------------------------
# Pipeline composition
# ---------------------------------------------------------------------------
def pipeline_by_stage(user: AppUser) -> list[dict]:
    open_opps = scoping.scoped_opportunities(user).filter(
        status=Opportunity.Status.OPEN
    )
    rows = {
        row["stage"]: row
        for row in open_opps.values("stage").annotate(
            count=Count("id"),
            value=_ESTIMATED_SUM,
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


def pipeline_by_estimator(user: AppUser) -> list[dict]:
    qs = (
        scoping.scoped_opportunities(user)
        .filter(
            status=Opportunity.Status.OPEN,
            estimator__isnull=False,
        )
        .values(
            "estimator_id",
            "estimator__username",
            "estimator__display_name",
        )
        .annotate(
            open_count=Count("id"),
            open_value=_ESTIMATED_SUM,
        )
        .order_by("-open_value")
    )
    return [
        {
            "estimator_id": r["estimator_id"],
            "username": r["estimator__username"],
            "display_name": r["estimator__display_name"],
            "open_count": r["open_count"],
            "open_value": r["open_value"],
        }
        for r in qs
    ]


# ---------------------------------------------------------------------------
# Overdue follow-ups
# ---------------------------------------------------------------------------
def overdue_followups_report(user: AppUser) -> list[dict]:
    today = timezone.localdate()
    qs = (
        scoping.scoped_followups(user)
        .exclude(
            status__in=[
                FollowUpTask.Status.COMPLETED,
                FollowUpTask.Status.CANCELLED,
            ]
        )
        .filter(due_date__lt=today)
        .select_related(
            "opportunity",
            "opportunity__company",
            "assigned_to_user",
        )
        .order_by("due_date")
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
                    t.opportunity.company.name
                    if t.opportunity.company_id
                    else None
                ),
            },
            "assigned_to_user": {
                "id": t.assigned_to_user_id,
                "username": t.assigned_to_user.username,
                "display_name": t.assigned_to_user.display_name,
            },
        }
        for t in qs
    ]


# ---------------------------------------------------------------------------
# Win rates
# ---------------------------------------------------------------------------
def _with_win_rate(row: dict) -> float:
    decided = row["decided"]
    won = row["won"]
    return round((won / decided) * 100, 2) if decided else 0.0


def win_rate_by_estimator(user: AppUser) -> list[dict]:
    qs = (
        scoping.scoped_opportunities(user)
        .filter(
            estimator__isnull=False,
            stage__in=[Opportunity.Stage.WON, Opportunity.Stage.LOST],
        )
        .values(
            "estimator_id",
            "estimator__username",
            "estimator__display_name",
        )
        .annotate(
            decided=Count("id"),
            won=Count("id", filter=Q(stage=Opportunity.Stage.WON)),
            lost=Count("id", filter=Q(stage=Opportunity.Stage.LOST)),
            won_value=_won_value_sum(),
        )
        .order_by("-won_value")
    )
    return [
        {
            "estimator_id": r["estimator_id"],
            "username": r["estimator__username"],
            "display_name": r["estimator__display_name"],
            "decided": r["decided"],
            "won": r["won"],
            "lost": r["lost"],
            "won_value": r["won_value"],
            "win_rate_percent": _with_win_rate(r),
        }
        for r in qs
    ]


def win_rate_by_company(user: AppUser) -> list[dict]:
    qs = (
        scoping.scoped_opportunities(user)
        .filter(stage__in=[Opportunity.Stage.WON, Opportunity.Stage.LOST])
        .values("company_id", "company__name", "company__company_type")
        .annotate(
            decided=Count("id"),
            won=Count("id", filter=Q(stage=Opportunity.Stage.WON)),
            lost=Count("id", filter=Q(stage=Opportunity.Stage.LOST)),
            won_value=_won_value_sum(),
        )
        .order_by("-won_value")
    )
    return [
        {
            "company_id": r["company_id"],
            "company_name": r["company__name"],
            "company_type": r["company__company_type"],
            "decided": r["decided"],
            "won": r["won"],
            "lost": r["lost"],
            "won_value": r["won_value"],
            "win_rate_percent": _with_win_rate(r),
        }
        for r in qs
    ]


# ---------------------------------------------------------------------------
# Loss reasons
# ---------------------------------------------------------------------------
def loss_reasons_report(user: AppUser) -> list[dict]:
    lost_ids = scoping.scoped_opportunities(user).filter(
        stage=Opportunity.Stage.LOST
    ).values_list("id", flat=True)

    qs = (
        LossReason.objects.filter(opportunity_id__in=lost_ids)
        .values("reason_category")
        .annotate(
            count=Count("id"),
            estimated_value=Coalesce(
                Sum("opportunity__estimated_contract_value"),
                ZERO_DEC,
                output_field=DecimalField(max_digits=16, decimal_places=2),
            ),
        )
        .order_by("-count")
    )
    label_map = {c.value: c.label for c in LossReason.Category}
    return [
        {
            "reason_category": r["reason_category"],
            "reason_label": label_map.get(
                r["reason_category"], r["reason_category"]
            ),
            "count": r["count"],
            "estimated_value": r["estimated_value"],
        }
        for r in qs
    ]


# ---------------------------------------------------------------------------
# Stale opportunities (no activity in the last `days` days)
# ---------------------------------------------------------------------------
def stale_opportunities(user: AppUser, days: int = 14) -> list[dict]:
    now = timezone.now()
    cutoff = now - timedelta(days=days)

    qs = (
        scoping.scoped_opportunities(user)
        .filter(status=Opportunity.Status.OPEN)
        .annotate(last_activity_at=Max("activity_logs__created_at"))
        .filter(Q(last_activity_at__lt=cutoff) | Q(last_activity_at__isnull=True))
        .select_related("company", "estimator", "assigned_user")
        .order_by("updated_at")
    )

    results = []
    for o in qs:
        last = o.last_activity_at
        results.append(
            {
                "id": o.id,
                "project_name": o.project_name,
                "project_code": o.project_code,
                "stage": o.stage,
                "company": {
                    "id": o.company_id,
                    "name": o.company.name if o.company_id else None,
                },
                "estimator": (
                    {
                        "id": o.estimator_id,
                        "display_name": o.estimator.display_name,
                    }
                    if o.estimator_id
                    else None
                ),
                "assigned_user": (
                    {
                        "id": o.assigned_user_id,
                        "display_name": o.assigned_user.display_name,
                    }
                    if o.assigned_user_id
                    else None
                ),
                "estimated_contract_value": o.estimated_contract_value,
                "last_activity_at": last,
                "days_since_last_activity": (
                    (now - last).days if last else None
                ),
                "last_updated_at": o.updated_at,
            }
        )
    return results

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

from ..models import FollowUpTask, LossReason, Opportunity, Quote
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
_STALE_STAGES = (
    Opportunity.Stage.SUBMITTED,
    Opportunity.Stage.FOLLOW_UP,
    Opportunity.Stage.NEGOTIATING,
)

STALE_THRESHOLD_DAYS = 30


def _submission_date_for(opp: Opportunity):
    """
    Resolve the effective submission date for a stale calculation using
    the documented priority:

      1. Opportunity.submission_date
      2. latest Quote.submission_date (highest revision with a date)
      3. latest submitted Quote.created_at
      4. Opportunity.updated_at — fallback only when no submitted date
         exists anywhere.

    Returns a (date, is_true_submission) tuple. ``is_true_submission``
    is False only when the ``updated_at`` fallback was used, so callers
    can treat that case conservatively.
    """
    if opp.submission_date:
        return opp.submission_date, True

    quotes = list(opp.quotes.all())

    # 2. latest quote that carries a submission_date (by revision).
    dated = [q for q in quotes if q.submission_date]
    if dated:
        dated.sort(key=lambda q: q.revision_number, reverse=True)
        return dated[0].submission_date, True

    # 3. latest submitted quote's created_at.
    submitted = [
        q for q in quotes if q.quote_status == Quote.QuoteStatus.SUBMITTED
    ]
    if submitted:
        submitted.sort(key=lambda q: q.revision_number, reverse=True)
        return submitted[0].created_at.date(), True

    # 4. fallback.
    return opp.updated_at.date(), False


def stale_opportunities(user: AppUser, days: int = STALE_THRESHOLD_DAYS) -> list[dict]:
    """
    An opportunity is stale when ALL of the following hold:
      - not archived
      - stage is submitted, follow_up, or negotiating (never won/lost)
      - at least ``days`` days (default 30) since its effective
        submission date
      - it has no pending/in-progress follow-up whose due_date >= today
    """
    if days < 1:
        days = STALE_THRESHOLD_DAYS
    today = timezone.localdate()
    cutoff = today - timedelta(days=days)

    active_statuses = (
        FollowUpTask.Status.PENDING,
        FollowUpTask.Status.IN_PROGRESS,
    )

    qs = (
        scoping.scoped_opportunities(user)  # already excludes archived
        .filter(stage__in=_STALE_STAGES)
        # _STALE_STAGES already excludes won/lost/withdrawn, but be
        # explicit that anything closed off (e.g. marked won) drops out
        # of the stale list regardless of stage.
        .exclude(status=Opportunity.Status.CLOSED)
        .select_related("company", "estimator", "assigned_user")
        .prefetch_related("quotes", "tasks")
    )

    results = []
    for o in qs:
        submission_date, _is_true = _submission_date_for(o)
        days_since = (today - submission_date).days

        # Not old enough yet.
        if submission_date > cutoff:
            continue

        # Look at this opportunity's follow-ups.
        tasks = list(o.tasks.all())
        future_pending = [
            t
            for t in tasks
            if t.status in active_statuses and t.due_date >= today
        ]
        # A pending future follow-up means someone is on it — not stale.
        if future_pending:
            continue

        # Report metadata: most recent completed/any follow-up date, and
        # the soonest upcoming follow-up date (there is none if we got
        # here, but keep the field for the frontend).
        past_due_dates = [t.due_date for t in tasks]
        last_followup_date = max(past_due_dates) if past_due_dates else None
        next_followup_date = None  # by definition no future pending one

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
                "stale_since_date": submission_date,
                "days_since_submission": days_since,
                "last_followup_date": last_followup_date,
                "next_followup_date": next_followup_date,
            }
        )

    # Oldest submissions first.
    results.sort(key=lambda r: r["stale_since_date"])
    return results

"""
Role-aware queryset scoping for pipeline resources.

Every dashboard / report / viewset goes through these helpers instead of
touching ``Model.objects`` directly. This is the single place where
row-level visibility rules live — the DRF permission classes control
*what* a role can do, and these functions control *what rows they can
see at all*.

Rule summary
------------
- Director, Admin, Estimator, Read-Only, Superuser
    Unrestricted visibility. Their ability to write is controlled by
    the permission classes in apps/pipeline/permissions.py.

- Project Manager
    Sees only opportunities whose ``stage == "won"`` and records that
    belong to those opportunities (quotes, tasks, activity, companies,
    contacts, loss reasons). Rationale: PMs run awarded jobs; they do
    not need visibility into live tender workflow.
"""
from __future__ import annotations

from django.db.models import QuerySet

from apps.users.models import AppUser

from ..models import (
    ActivityLog,
    Company,
    Contact,
    FollowUpTask,
    LossReason,
    Opportunity,
    Quote,
)

Role = AppUser.Role


def _role(user) -> str | None:
    return getattr(user, "role", None)


def _sees_everything(user) -> bool:
    """Roles whose visibility is unrestricted."""
    if user is None or not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    return _role(user) in (
        Role.DIRECTOR,
        Role.ESTIMATOR,
        Role.ADMIN,
        Role.READ_ONLY,
    )


# ---------------------------------------------------------------------------
# Pipeline objects
# ---------------------------------------------------------------------------
def scoped_opportunities(
    user, *, include_archived: bool = False
) -> QuerySet[Opportunity]:
    """
    Row-level visible opportunities for ``user``. Archived opportunities
    are excluded by default; pass ``include_archived=True`` to include
    them (e.g. for the archived-opportunity restore UI).
    """
    if _sees_everything(user):
        qs = Opportunity.objects.all()
    elif _role(user) == Role.PROJECT_MANAGER:
        qs = Opportunity.objects.filter(stage=Opportunity.Stage.WON)
    else:
        qs = Opportunity.objects.none()
    if not include_archived:
        qs = qs.filter(archived_at__isnull=True)
    return qs


def scoped_quotes(user, *, include_archived: bool = False) -> QuerySet[Quote]:
    if _sees_everything(user):
        qs = Quote.objects.all()
    elif _role(user) == Role.PROJECT_MANAGER:
        qs = Quote.objects.filter(opportunity__stage=Opportunity.Stage.WON)
    else:
        qs = Quote.objects.none()
    if not include_archived:
        qs = qs.filter(opportunity__archived_at__isnull=True)
    return qs


def scoped_followups(
    user, *, include_archived: bool = False
) -> QuerySet[FollowUpTask]:
    if _sees_everything(user):
        qs = FollowUpTask.objects.all()
    elif _role(user) == Role.PROJECT_MANAGER:
        qs = FollowUpTask.objects.filter(
            opportunity__stage=Opportunity.Stage.WON
        )
    else:
        qs = FollowUpTask.objects.none()
    if not include_archived:
        qs = qs.filter(opportunity__archived_at__isnull=True)
    return qs


def scoped_activity(user) -> QuerySet[ActivityLog]:
    """
    Activity logs are an audit trail — they are never filtered by
    archive state. Archiving an opportunity does NOT hide its activity
    history; otherwise the "archived" event itself would vanish.
    """
    if _sees_everything(user):
        return ActivityLog.objects.all()
    if _role(user) == Role.PROJECT_MANAGER:
        return ActivityLog.objects.filter(
            opportunity__stage=Opportunity.Stage.WON
        )
    return ActivityLog.objects.none()


def scoped_loss_reasons(
    user, *, include_archived: bool = False
) -> QuerySet[LossReason]:
    if _sees_everything(user):
        qs = LossReason.objects.all()
    else:
        qs = LossReason.objects.none()
    if not include_archived:
        qs = qs.filter(opportunity__archived_at__isnull=True)
    return qs


# ---------------------------------------------------------------------------
# Reference data
# ---------------------------------------------------------------------------
def scoped_companies(user) -> QuerySet[Company]:
    if _sees_everything(user):
        return Company.objects.all()
    if _role(user) == Role.PROJECT_MANAGER:
        return Company.objects.filter(
            opportunities__stage=Opportunity.Stage.WON
        ).distinct()
    return Company.objects.none()


def scoped_contacts(user) -> QuerySet[Contact]:
    if _sees_everything(user):
        return Contact.objects.all()
    if _role(user) == Role.PROJECT_MANAGER:
        return Contact.objects.filter(
            company__opportunities__stage=Opportunity.Stage.WON
        ).distinct()
    return Contact.objects.none()

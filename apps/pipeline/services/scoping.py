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
def scoped_opportunities(user) -> QuerySet[Opportunity]:
    if _sees_everything(user):
        return Opportunity.objects.all()
    if _role(user) == Role.PROJECT_MANAGER:
        return Opportunity.objects.filter(stage=Opportunity.Stage.WON)
    return Opportunity.objects.none()


def scoped_quotes(user) -> QuerySet[Quote]:
    if _sees_everything(user):
        return Quote.objects.all()
    if _role(user) == Role.PROJECT_MANAGER:
        return Quote.objects.filter(opportunity__stage=Opportunity.Stage.WON)
    return Quote.objects.none()


def scoped_followups(user) -> QuerySet[FollowUpTask]:
    if _sees_everything(user):
        return FollowUpTask.objects.all()
    if _role(user) == Role.PROJECT_MANAGER:
        return FollowUpTask.objects.filter(opportunity__stage=Opportunity.Stage.WON)
    return FollowUpTask.objects.none()


def scoped_activity(user) -> QuerySet[ActivityLog]:
    if _sees_everything(user):
        return ActivityLog.objects.all()
    if _role(user) == Role.PROJECT_MANAGER:
        return ActivityLog.objects.filter(opportunity__stage=Opportunity.Stage.WON)
    return ActivityLog.objects.none()


def scoped_loss_reasons(user) -> QuerySet[LossReason]:
    if _sees_everything(user):
        return LossReason.objects.all()
    # Project managers only see won opportunities, which never have a
    # loss reason, so this is always empty for them.
    return LossReason.objects.none()


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

"""
Role-aware queryset scoping hooks.

Every dashboard/report function goes through these helpers instead of
touching ``Model.objects`` directly. Today the functions just return the
full queryset — RBAC is not wired up yet — but centralising the access
point here means that when role-based scoping lands (for example,
estimators only seeing their own opportunities, read-only users seeing
everything), the dashboard and report code does not need to change.
"""
from __future__ import annotations

from django.db.models import QuerySet

from apps.users.models import AppUser

from ..models import ActivityLog, FollowUpTask, Opportunity, Quote


def scoped_opportunities(user: AppUser) -> QuerySet[Opportunity]:
    return Opportunity.objects.all()


def scoped_followups(user: AppUser) -> QuerySet[FollowUpTask]:
    return FollowUpTask.objects.all()


def scoped_quotes(user: AppUser) -> QuerySet[Quote]:
    return Quote.objects.all()


def scoped_activity(user: AppUser) -> QuerySet[ActivityLog]:
    return ActivityLog.objects.all()

"""
DRF permission classes for the pipeline app.

Backend-only enforcement: these classes are the single source of truth for
which roles may perform which action. The frontend should consult the same
rules for UI affordances, but must never be trusted for authorisation.

The companion row-level filtering lives in
``apps/pipeline/services/scoping.py`` and is applied in each viewset's
``get_queryset``.
"""
from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.users.models import AppUser

Role = AppUser.Role


# ---------------------------------------------------------------------------
# Relevance rule (single canonical definition)
#
# An opportunity is "relevant" to a user when that user is either the
# designated estimator or the assigned_user on the opportunity. This is the
# one rule used wherever a role is restricted to "their own" pipeline:
#
#   - estimators creating / editing / deleting follow-up tasks
#
# If we ever need another "ownership"-style rule elsewhere, change it here
# (and only here) so the definition never drifts.
# ---------------------------------------------------------------------------
def is_relevant_opportunity(opportunity, user) -> bool:
    if opportunity is None or user is None or not user.is_authenticated:
        return False
    return (
        opportunity.estimator_id == user.id
        or opportunity.assigned_user_id == user.id
    )


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _role(user) -> str | None:
    return getattr(user, "role", None)


def _is_director_level(user) -> bool:
    """Directors and Django superusers have unrestricted access."""
    return bool(user and (user.is_superuser or _role(user) == Role.DIRECTOR))


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------
class IsAuthenticatedActive(BasePermission):
    """All pipeline endpoints require an active authenticated user."""

    def has_permission(self, request, view):
        user = request.user
        return bool(user and user.is_authenticated and user.is_active)


# ---------------------------------------------------------------------------
# Reference data (companies, contacts)
# ---------------------------------------------------------------------------
class CompanyPermission(IsAuthenticatedActive):
    """
    Companies are reference data.

    Read:   any authenticated user.
    Write:  director, admin.
    Delete: director, admin.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _is_director_level(request.user) or _role(request.user) == Role.ADMIN


class ContactPermission(CompanyPermission):
    """Contacts follow the same rules as companies."""


# ---------------------------------------------------------------------------
# Opportunities
# ---------------------------------------------------------------------------
class OpportunityPermission(IsAuthenticatedActive):
    """
    Read:
        any authenticated user. Row-level visibility is enforced
        separately by ``scoping.scoped_opportunities``.

    Create / update:
        director, estimator, admin. Admins are additionally blocked from
        modifying pricing-sensitive fields in OpportunityViewSet (see
        ``ADMIN_OPPORTUNITY_PROTECTED_FIELDS``).

    mark_won / mark_lost:
        director, estimator only. These are business decisions with
        pricing implications; admin cannot trigger them.

    Destroy:
        director only. Deleting an opportunity wipes its quotes, tasks
        and activity log via cascade.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True

        user = request.user
        if _is_director_level(user):
            return True

        role = _role(user)
        action = getattr(view, "action", None)

        if action == "destroy":
            return False

        if action in ("mark_won", "mark_lost"):
            return role == Role.ESTIMATOR

        if action in ("create", "update", "partial_update"):
            return role in (Role.ESTIMATOR, Role.ADMIN)

        return False


# ---------------------------------------------------------------------------
# Quotes (pricing control)
# ---------------------------------------------------------------------------
class QuotePermission(IsAuthenticatedActive):
    """
    Read:    any authenticated user.
    Write:   director, estimator only.
    Destroy: director only.

    Admins, project managers and read-only users cannot write quotes.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        if _is_director_level(request.user):
            return True
        action = getattr(view, "action", None)
        if action == "destroy":
            return False
        return _role(request.user) == Role.ESTIMATOR


# ---------------------------------------------------------------------------
# Follow-up tasks
# ---------------------------------------------------------------------------
class FollowUpTaskPermission(IsAuthenticatedActive):
    """
    Read:
        any authenticated user.

    Create:
        director, admin (any opportunity).
        estimator (only when the target opportunity is relevant to them;
        enforced in ``FollowUpTaskViewSet.perform_create`` because the
        object does not exist yet at permission time).

    Update / destroy:
        director, admin.
        estimator only when the existing task's opportunity is relevant.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        if _is_director_level(request.user):
            return True
        return _role(request.user) in (Role.ADMIN, Role.ESTIMATOR)

    def has_object_permission(self, request, view, obj):
        if request.method in SAFE_METHODS:
            return True
        if _is_director_level(request.user):
            return True
        role = _role(request.user)
        if role == Role.ADMIN:
            return True
        if role == Role.ESTIMATOR:
            return is_relevant_opportunity(obj.opportunity, request.user)
        return False


# ---------------------------------------------------------------------------
# Activity log
# ---------------------------------------------------------------------------
class ActivityLogPermission(IsAuthenticatedActive):
    """
    The activity log is append-only for everyone except directors.

    Read:   any authenticated user.
    Create: director, estimator, admin.
    Update / destroy: director only.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        if _is_director_level(request.user):
            return True
        action = getattr(view, "action", None)
        if action in ("update", "partial_update", "destroy"):
            return False
        return _role(request.user) in (Role.ESTIMATOR, Role.ADMIN)


# ---------------------------------------------------------------------------
# Loss reasons
# ---------------------------------------------------------------------------
class LossReasonPermission(IsAuthenticatedActive):
    """
    Read:  any authenticated user (queryset scoping may still hide them).
    Write: director only. The normal way to record a loss is
           ``POST /api/opportunities/{id}/mark_lost/`` which runs under
           OpportunityPermission and creates the LossReason server-side.
    """

    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        if request.method in SAFE_METHODS:
            return True
        return _is_director_level(request.user)

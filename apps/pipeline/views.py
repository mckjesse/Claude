from django.db import transaction
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.users.models import AppUser

from .filters import FollowUpTaskFilter, OpportunityFilter
from .models import (
    ActivityLog,
    Company,
    Contact,
    FollowUpTask,
    LossReason,
    Opportunity,
    Quote,
)
from .permissions import (
    ActivityLogPermission,
    CompanyPermission,
    ContactPermission,
    FollowUpTaskPermission,
    LossReasonPermission,
    OpportunityPermission,
    QuotePermission,
    is_relevant_opportunity,
)
from .serializers import (
    ActivityLogSerializer,
    CompanySerializer,
    ContactSerializer,
    FollowUpTaskSerializer,
    LossReasonSerializer,
    MarkLostSerializer,
    MarkWonSerializer,
    OpportunitySerializer,
    QuoteSerializer,
)
from .services import activity
from .services import dashboard as dashboard_service
from .services import followup_automation
from .services import quote_automation
from .services import reports as reports_service
from .services import scoping

# ---------------------------------------------------------------------------
# Fields on Opportunity that admins are never allowed to touch directly.
# Enforced in ``OpportunityViewSet._enforce_admin_field_protection``.
# Admins can still edit every other field (project_name, code, company,
# contact, scope text, dates, etc).
# ---------------------------------------------------------------------------
ADMIN_OPPORTUNITY_PROTECTED_FIELDS = frozenset(
    {
        "estimated_contract_value",
        "estimated_margin_percent",
        "probability_percent",
        "final_awarded_value",
        "stage",
    }
)


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [CompanyPermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["company_type", "status", "state"]
    search_fields = ["name", "primary_email", "suburb", "state"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["name"]
    queryset = Company.objects.all()

    def get_queryset(self):
        return scoping.scoped_companies(self.request.user)


class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [ContactPermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["company", "status", "preferred_contact_method"]
    search_fields = ["first_name", "last_name", "email", "company__name"]
    ordering_fields = ["last_name", "first_name", "created_at"]
    ordering = ["last_name", "first_name"]
    queryset = Contact.objects.all()

    def get_queryset(self):
        return scoping.scoped_contacts(self.request.user).select_related("company")


class OpportunityViewSet(viewsets.ModelViewSet):
    serializer_class = OpportunitySerializer
    permission_classes = [OpportunityPermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = OpportunityFilter
    search_fields = [
        "project_name",
        "project_code",
        "company__name",
        "site_suburb",
    ]
    ordering_fields = [
        "project_name",
        "stage",
        "submission_due_date",
        "expected_award_date",
        "estimated_contract_value",
        "probability_percent",
        "created_at",
        "updated_at",
    ]
    ordering = ["-created_at"]
    queryset = Opportunity.objects.all()

    def get_queryset(self):
        # ``?archived=`` controls archive visibility on the list view:
        #   (unset or any other value)  → active opportunities only
        #   true                        → archived opportunities only
        #   all                         → both active and archived
        archived_param = (
            self.request.query_params.get("archived", "").lower()
        )
        include_archived = archived_param in ("true", "all")
        qs = scoping.scoped_opportunities(
            self.request.user, include_archived=include_archived
        )
        if archived_param == "true":
            qs = qs.filter(archived_at__isnull=False)
        return (
            qs.select_related(
                "company",
                "primary_contact",
                "estimator",
                "assigned_user",
                "loss_reason",
                "archived_by",
            )
            .prefetch_related("quotes", "tasks")
        )

    # ------------------------------------------------------------------
    # Admin field-level protection
    #
    # Admins can help administer opportunities (metadata, scope text,
    # dates, assignments) but must never set or change pricing or stage.
    # Rather than split the serializer, we inspect validated_data on
    # create/update and reject protected fields with PermissionDenied.
    # ------------------------------------------------------------------
    def _enforce_admin_field_protection(self, serializer):
        user = self.request.user
        if user.is_superuser:
            return
        if getattr(user, "role", None) != AppUser.Role.ADMIN:
            return
        protected = set(serializer.validated_data) & ADMIN_OPPORTUNITY_PROTECTED_FIELDS
        if protected:
            raise PermissionDenied(
                "Admins cannot modify pricing or stage fields: "
                + ", ".join(sorted(protected))
            )

    def perform_create(self, serializer):
        self._enforce_admin_field_protection(serializer)
        with transaction.atomic():
            opp = serializer.save()
            user = self.request.user
            activity.opportunity_created(opp, user)
            quote_automation.sync_quote_from_opportunity(opp, user=user)
            followup_automation.sync_followup_from_opportunity(
                opp, user=user, old_stage=None,
            )

    def perform_update(self, serializer):
        self._enforce_admin_field_protection(serializer)
        instance = serializer.instance
        baseline = activity.snapshot(
            instance, activity.OPPORTUNITY_TRACKED_FIELDS
        )
        old_stage = instance.stage
        with transaction.atomic():
            opp = serializer.save()
            changed = activity.diff(opp, baseline)
            user = self.request.user
            if opp.stage != old_stage:
                activity.opportunity_stage_changed(
                    opp, user, old_stage, opp.stage
                )
            activity.opportunity_updated(opp, user, changed)
            quote_automation.sync_quote_from_opportunity(opp, user=user)
            followup_automation.sync_followup_from_opportunity(
                opp, user=user, old_stage=old_stage,
            )

    @action(detail=True, methods=["post"])
    def mark_won(self, request, pk=None):
        opp = self.get_object()
        payload = MarkWonSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with transaction.atomic():
            opp.final_awarded_value = payload.validated_data["final_awarded_value"]
            opp.stage = Opportunity.Stage.WON
            opp.status = Opportunity.Status.CLOSED
            opp.save(
                update_fields=[
                    "final_awarded_value",
                    "stage",
                    "status",
                    "updated_at",
                ]
            )
            activity.opportunity_marked_won(
                opp, request.user, opp.final_awarded_value
            )
            quote_automation.sync_quote_from_opportunity(
                opp, user=request.user
            )
        return Response(self.get_serializer(opp).data)

    @action(detail=True, methods=["post"])
    def mark_lost(self, request, pk=None):
        opp = self.get_object()
        payload = MarkLostSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        with transaction.atomic():
            LossReason.objects.update_or_create(
                opportunity=opp,
                defaults=payload.validated_data,
            )
            opp.stage = Opportunity.Stage.LOST
            opp.status = Opportunity.Status.CLOSED
            opp.save(update_fields=["stage", "status", "updated_at"])
            activity.opportunity_marked_lost(
                opp,
                request.user,
                payload.validated_data["reason_category"],
                payload.validated_data.get("competitor_name", ""),
            )
            quote_automation.sync_quote_from_opportunity(
                opp, user=request.user
            )
        return Response(self.get_serializer(opp).data)

    @action(detail=True, methods=["post"])
    def reopen(self, request, pk=None):
        """
        POST /api/opportunities/{id}/reopen/

        Moves a won or lost opportunity back into the active pipeline.
        The historical loss reason (if any) is preserved for audit —
        it is NOT deleted. Existing quote records are left untouched
        (no status change, no deletion) so the pricing history remains
        intact.

        Access: same roles that can use mark_won / mark_lost
        (director and estimator).
        """
        opp = self.get_object()
        if opp.stage not in (
            Opportunity.Stage.WON,
            Opportunity.Stage.LOST,
        ):
            return Response(
                {
                    "detail": (
                        f"Only won or lost opportunities can be reopened. "
                        f"This opportunity is currently '{opp.stage}'."
                    )
                },
                status=400,
            )
        old_stage = opp.stage
        with transaction.atomic():
            opp.stage = Opportunity.Stage.FOLLOW_UP
            opp.status = Opportunity.Status.OPEN
            opp.save(update_fields=["stage", "status", "updated_at"])
            activity.opportunity_stage_changed(
                opp, request.user, old_stage, opp.stage
            )
            activity._log(
                opportunity=opp,
                entity_type="opportunity",
                entity_id=opp.id,
                activity_type="reopened",
                description=(
                    f"Opportunity reopened from {old_stage}. "
                    f"Moved to {Opportunity.Stage.FOLLOW_UP.label}."
                ),
                user=request.user,
            )
        return Response(self.get_serializer(opp).data)

    def _get_opportunity_for_archive_path(self, request, pk):
        """
        Resolve an opportunity for archive / restore / destroy even
        when it is already archived and therefore hidden by the
        default queryset.
        """
        return (
            scoping.scoped_opportunities(
                request.user, include_archived=True
            )
            .filter(pk=pk)
            .first()
        )

    @action(detail=True, methods=["post"])
    def archive(self, request, pk=None):
        """
        POST /api/opportunities/{id}/archive/

        Soft-delete: hides the opportunity from normal list / dashboard
        / report queries without deleting any rows. Stage and status
        are left alone (an open opportunity can be archived and will
        come back open when restored; a lost opportunity stays lost).
        """
        opp = self._get_opportunity_for_archive_path(request, pk)
        if opp is None:
            return Response({"detail": "Not found."}, status=404)
        if opp.archived_at is not None:
            return Response(
                {"detail": "Opportunity is already archived."},
                status=400,
            )
        with transaction.atomic():
            opp.archived_at = timezone.now()
            opp.archived_by = request.user
            opp.save(update_fields=["archived_at", "archived_by", "updated_at"])
            activity.opportunity_archived(opp, request.user)
        return Response(self.get_serializer(opp).data)

    @action(detail=True, methods=["post"])
    def restore(self, request, pk=None):
        """
        POST /api/opportunities/{id}/restore/

        Undo archive. Stage and status are untouched — the opportunity
        returns to the exact state it was in before archive.
        """
        opp = self._get_opportunity_for_archive_path(request, pk)
        if opp is None:
            return Response({"detail": "Not found."}, status=404)
        if opp.archived_at is None:
            return Response(
                {"detail": "Opportunity is not archived."},
                status=400,
            )
        with transaction.atomic():
            opp.archived_at = None
            opp.archived_by = None
            opp.save(update_fields=["archived_at", "archived_by", "updated_at"])
            activity.opportunity_restored(opp, request.user)
        return Response(self.get_serializer(opp).data)

    def destroy(self, request, *args, **kwargs):
        """
        Hard DELETE. Only permitted on opportunities that have already
        been archived — callers must go through POST /archive/ first.
        That ensures the archive step is always logged in the activity
        feed even if the admin eventually hard-deletes the row. The
        permission class (OpportunityPermission) restricts this to
        director + superuser.
        """
        opp = self._get_opportunity_for_archive_path(
            request, kwargs.get("pk")
        )
        if opp is None:
            return Response({"detail": "Not found."}, status=404)
        if opp.archived_at is None:
            return Response(
                {
                    "detail": (
                        "Opportunity must be archived before it can be "
                        "permanently deleted. "
                        "POST /api/opportunities/{id}/archive/ first."
                    )
                },
                status=400,
            )
        opp.delete()
        return Response(status=204)


class QuoteViewSet(viewsets.ModelViewSet):
    serializer_class = QuoteSerializer
    permission_classes = [QuotePermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["opportunity", "quote_status"]
    search_fields = ["quote_reference", "opportunity__project_name"]
    ordering_fields = ["revision_number", "submission_date", "created_at"]
    ordering = ["opportunity", "-revision_number"]
    queryset = Quote.objects.all()

    def get_queryset(self):
        return scoping.scoped_quotes(self.request.user).select_related(
            "opportunity",
            "opportunity__company",
        )

    def perform_create(self, serializer):
        with transaction.atomic():
            quote = serializer.save()
            activity.quote_created(quote, self.request.user)

    def perform_update(self, serializer):
        baseline = activity.snapshot(
            serializer.instance, activity.QUOTE_TRACKED_FIELDS
        )
        with transaction.atomic():
            quote = serializer.save()
            changed = activity.diff(quote, baseline)
            activity.quote_updated(quote, self.request.user, changed)


class FollowUpTaskViewSet(viewsets.ModelViewSet):
    serializer_class = FollowUpTaskSerializer
    permission_classes = [FollowUpTaskPermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = FollowUpTaskFilter
    search_fields = ["subject", "details", "opportunity__project_name"]
    ordering_fields = ["due_date", "priority", "status", "created_at"]
    ordering = ["due_date", "due_time"]
    queryset = FollowUpTask.objects.all()

    def get_queryset(self):
        return scoping.scoped_followups(self.request.user).select_related(
            "opportunity",
            "opportunity__company",
            "assigned_to_user",
            "related_quote",
        )

    def perform_create(self, serializer):
        # Estimators can only attach follow-ups to opportunities that are
        # "relevant" to them (same rule as has_object_permission for
        # update/delete). Directors, admins and superusers are unrestricted.
        user = self.request.user
        role = getattr(user, "role", None)
        if (
            not user.is_superuser
            and role == AppUser.Role.ESTIMATOR
        ):
            opp = serializer.validated_data.get("opportunity")
            if not is_relevant_opportunity(opp, user):
                raise PermissionDenied(
                    "You can only create follow-ups on opportunities "
                    "where you are the estimator or the assigned user."
                )
        with transaction.atomic():
            task = serializer.save()
            activity.followup_created(task, user)

    def perform_update(self, serializer):
        instance = serializer.instance
        baseline = activity.snapshot(instance, activity.FOLLOWUP_TRACKED_FIELDS)
        old_status = instance.status
        with transaction.atomic():
            task = serializer.save()
            user = self.request.user
            changed = activity.diff(task, baseline)
            if (
                old_status != FollowUpTask.Status.COMPLETED
                and task.status == FollowUpTask.Status.COMPLETED
            ):
                activity.followup_completed(task, user)
            activity.followup_updated(task, user, changed)


class ActivityLogViewSet(viewsets.ModelViewSet):
    serializer_class = ActivityLogSerializer
    permission_classes = [ActivityLogPermission]
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["opportunity", "activity_type", "entity_type"]
    search_fields = ["description", "opportunity__project_name"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]
    queryset = ActivityLog.objects.all()

    def get_queryset(self):
        return scoping.scoped_activity(self.request.user).select_related(
            "opportunity",
            "opportunity__company",
            "created_by_user",
        )


class LossReasonViewSet(viewsets.ModelViewSet):
    serializer_class = LossReasonSerializer
    permission_classes = [LossReasonPermission]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["reason_category"]
    ordering_fields = ["recorded_at"]
    ordering = ["-recorded_at"]
    queryset = LossReason.objects.all()

    def get_queryset(self):
        return scoping.scoped_loss_reasons(self.request.user).select_related(
            "opportunity",
            "opportunity__company",
        )


class LossReasonChoicesView(APIView):
    """
    GET /api/loss-reason-choices/

    Returns the list of valid loss-reason categories for the "Mark Lost"
    modal dropdown. Each entry has a ``value`` (sent back to
    ``POST /api/opportunities/{id}/mark_lost/`` as ``reason_category``)
    and a ``label`` (human-readable, for display).
    """

    def get(self, request):
        return Response(
            [
                {"value": choice.value, "label": choice.label}
                for choice in LossReason.Category
            ]
        )


# ---------------------------------------------------------------------------
# Dashboard + reporting endpoints
#
# These are thin wrappers around the service layer. Business logic lives in
# apps/pipeline/services/. Views just hand the authenticated user to the
# service and return the result. The service layer itself calls through
# scoping.scoped_*() so visibility rules apply here too.
# ---------------------------------------------------------------------------
class DashboardView(APIView):
    """GET /api/dashboard/ — aggregated snapshot for the landing page."""

    def get(self, request):
        return Response(dashboard_service.build_dashboard(request.user))


class PipelineByStageReportView(APIView):
    def get(self, request):
        return Response(reports_service.pipeline_by_stage(request.user))


class PipelineByEstimatorReportView(APIView):
    def get(self, request):
        return Response(reports_service.pipeline_by_estimator(request.user))


class OverdueFollowupsReportView(APIView):
    def get(self, request):
        return Response(reports_service.overdue_followups_report(request.user))


class WinRateByEstimatorReportView(APIView):
    def get(self, request):
        return Response(reports_service.win_rate_by_estimator(request.user))


class WinRateByCompanyReportView(APIView):
    def get(self, request):
        return Response(reports_service.win_rate_by_company(request.user))


class LossReasonsReportView(APIView):
    def get(self, request):
        return Response(reports_service.loss_reasons_report(request.user))


class StaleOpportunitiesReportView(APIView):
    def get(self, request):
        try:
            days = int(request.query_params.get("days", 14))
        except (TypeError, ValueError):
            days = 14
        if days < 1:
            days = 14
        return Response(
            reports_service.stale_opportunities(request.user, days=days)
        )

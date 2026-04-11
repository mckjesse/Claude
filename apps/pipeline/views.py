from django.db import transaction
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

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
from .services import dashboard as dashboard_service
from .services import reports as reports_service


class CompanyViewSet(viewsets.ModelViewSet):
    queryset = Company.objects.all()
    serializer_class = CompanySerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["company_type", "status", "state"]
    search_fields = ["name", "primary_email", "suburb", "state"]
    ordering_fields = ["name", "created_at", "updated_at"]
    ordering = ["name"]


class ContactViewSet(viewsets.ModelViewSet):
    queryset = Contact.objects.select_related("company")
    serializer_class = ContactSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["company", "status", "preferred_contact_method"]
    search_fields = ["first_name", "last_name", "email", "company__name"]
    ordering_fields = ["last_name", "first_name", "created_at"]
    ordering = ["last_name", "first_name"]


class OpportunityViewSet(viewsets.ModelViewSet):
    queryset = (
        Opportunity.objects.select_related(
            "company",
            "primary_contact",
            "estimator",
            "assigned_user",
        )
        .prefetch_related("quotes", "tasks")
    )
    serializer_class = OpportunitySerializer
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
        return Response(self.get_serializer(opp).data)


class QuoteViewSet(viewsets.ModelViewSet):
    queryset = Quote.objects.select_related(
        "opportunity",
        "opportunity__company",
    )
    serializer_class = QuoteSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["opportunity", "quote_status"]
    search_fields = ["quote_reference", "opportunity__project_name"]
    ordering_fields = ["revision_number", "submission_date", "created_at"]
    ordering = ["opportunity", "-revision_number"]


class FollowUpTaskViewSet(viewsets.ModelViewSet):
    queryset = FollowUpTask.objects.select_related(
        "opportunity",
        "opportunity__company",
        "assigned_to_user",
        "related_quote",
    )
    serializer_class = FollowUpTaskSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_class = FollowUpTaskFilter
    search_fields = ["subject", "details", "opportunity__project_name"]
    ordering_fields = ["due_date", "priority", "status", "created_at"]
    ordering = ["due_date", "due_time"]


class ActivityLogViewSet(viewsets.ModelViewSet):
    queryset = ActivityLog.objects.select_related(
        "opportunity",
        "created_by_user",
    )
    serializer_class = ActivityLogSerializer
    filter_backends = [
        DjangoFilterBackend,
        filters.SearchFilter,
        filters.OrderingFilter,
    ]
    filterset_fields = ["opportunity", "activity_type", "entity_type"]
    search_fields = ["description", "opportunity__project_name"]
    ordering_fields = ["created_at"]
    ordering = ["-created_at"]


class LossReasonViewSet(viewsets.ModelViewSet):
    queryset = LossReason.objects.select_related("opportunity")
    serializer_class = LossReasonSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ["reason_category"]
    ordering_fields = ["recorded_at"]
    ordering = ["-recorded_at"]


# ---------------------------------------------------------------------------
# Dashboard + reporting endpoints
#
# These are thin wrappers around the service layer. Business logic lives in
# apps/pipeline/services/. Views just hand the authenticated user to the
# service and return the result.
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

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    ActivityLogViewSet,
    CompanyViewSet,
    ContactViewSet,
    DashboardView,
    FollowUpTaskViewSet,
    LossReasonChoicesView,
    LossReasonViewSet,
    LossReasonsReportView,
    OpportunityViewSet,
    OverdueFollowupsReportView,
    PipelineByEstimatorReportView,
    PipelineByStageReportView,
    QuoteViewSet,
    StaleOpportunitiesReportView,
    WinRateByCompanyReportView,
    WinRateByEstimatorReportView,
)

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("contacts", ContactViewSet, basename="contact")
router.register("opportunities", OpportunityViewSet, basename="opportunity")
router.register("quotes", QuoteViewSet, basename="quote")
router.register("followups", FollowUpTaskViewSet, basename="followup")
router.register("activities", ActivityLogViewSet, basename="activity")
router.register("loss-reasons", LossReasonViewSet, basename="lossreason")

extra_patterns = [
    path(
        "loss-reason-choices/",
        LossReasonChoicesView.as_view(),
        name="loss-reason-choices",
    ),
    path(
        "loss-reasons/options/",
        LossReasonChoicesView.as_view(),
        name="loss-reason-options",
    ),
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    path(
        "reports/pipeline-by-stage/",
        PipelineByStageReportView.as_view(),
        name="report-pipeline-by-stage",
    ),
    path(
        "reports/pipeline-by-estimator/",
        PipelineByEstimatorReportView.as_view(),
        name="report-pipeline-by-estimator",
    ),
    path(
        "reports/overdue-followups/",
        OverdueFollowupsReportView.as_view(),
        name="report-overdue-followups",
    ),
    path(
        "reports/win-rate-by-estimator/",
        WinRateByEstimatorReportView.as_view(),
        name="report-win-rate-by-estimator",
    ),
    path(
        "reports/win-rate-by-company/",
        WinRateByCompanyReportView.as_view(),
        name="report-win-rate-by-company",
    ),
    path(
        "reports/loss-reasons/",
        LossReasonsReportView.as_view(),
        name="report-loss-reasons",
    ),
    path(
        "reports/stale-opportunities/",
        StaleOpportunitiesReportView.as_view(),
        name="report-stale-opportunities",
    ),
]

urlpatterns = extra_patterns + router.urls

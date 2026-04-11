from rest_framework.routers import DefaultRouter

from .views import (
    ActivityLogViewSet,
    CompanyViewSet,
    ContactViewSet,
    FollowUpTaskViewSet,
    LossReasonViewSet,
    OpportunityViewSet,
    QuoteViewSet,
)

router = DefaultRouter()
router.register("companies", CompanyViewSet, basename="company")
router.register("contacts", ContactViewSet, basename="contact")
router.register("opportunities", OpportunityViewSet, basename="opportunity")
router.register("quotes", QuoteViewSet, basename="quote")
router.register("followups", FollowUpTaskViewSet, basename="followup")
router.register("activities", ActivityLogViewSet, basename="activity")
router.register("loss-reasons", LossReasonViewSet, basename="lossreason")

urlpatterns = router.urls

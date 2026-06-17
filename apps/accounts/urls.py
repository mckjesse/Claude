from rest_framework.routers import DefaultRouter

from .views import BuilderViewSet, ContactViewSet

router = DefaultRouter()
router.register("builders", BuilderViewSet, basename="builder")
router.register("builder-contacts", ContactViewSet, basename="builder-contact")

urlpatterns = router.urls

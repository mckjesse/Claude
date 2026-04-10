from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'tools', views.ToolViewSet)
router.register(r'projects', views.ProjectViewSet)
router.register(r'history', views.AllocationHistoryViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('me/', views.me, name='me'),
]

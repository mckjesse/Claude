from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    CsrfView,
    CurrentUserView,
    LoginView,
    LogoutView,
    UserListView,
)

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("login/", LoginView.as_view(), name="user-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="user-logout"),
    path("me/", CurrentUserView.as_view(), name="user-me"),
    path("csrf/", CsrfView.as_view(), name="user-csrf"),
]

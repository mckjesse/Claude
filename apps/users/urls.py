from django.urls import path

from .views import CsrfView, CurrentUserView, LoginView, LogoutView, UserListView

urlpatterns = [
    path("", UserListView.as_view(), name="user-list"),
    path("csrf/", CsrfView.as_view(), name="user-csrf"),
    path("login/", LoginView.as_view(), name="user-login"),
    path("logout/", LogoutView.as_view(), name="user-logout"),
    path("me/", CurrentUserView.as_view(), name="user-me"),
]

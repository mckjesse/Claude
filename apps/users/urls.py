from django.urls import path

from .views import CurrentUserView, LoginView, LogoutView

urlpatterns = [
    path("login/", LoginView.as_view(), name="user-login"),
    path("logout/", LogoutView.as_view(), name="user-logout"),
    path("me/", CurrentUserView.as_view(), name="user-me"),
]

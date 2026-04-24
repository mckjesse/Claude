from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import AppUser
from .serializers import AppUserSerializer, LoginSerializer


class LoginView(APIView):
    """
    POST /api/users/login/

    Authenticates against Django's auth backend and returns JWT tokens
    plus the authenticated user's profile. No CSRF required — JWT auth
    is stateless.
    """

    permission_classes = [AllowAny]
    authentication_classes = []  # no auth needed to log in

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            username=serializer.validated_data["username"],
            password=serializer.validated_data["password"],
        )
        if user is None or not user.is_active:
            return Response(
                {"detail": "Invalid credentials."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "display_name": user.display_name,
                    "role": user.role,
                },
            }
        )


class LogoutView(APIView):
    """POST /api/users/logout/ — ends the Django session (if any)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class UserListView(APIView):
    """
    GET /api/users/

    Returns all active users. Used by the frontend to populate
    estimator / assigned_user dropdowns on the opportunity form.
    """

    def get(self, request):
        users = AppUser.objects.filter(is_active=True).order_by("username")
        return Response(AppUserSerializer(users, many=True).data)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """
    GET /api/users/csrf/

    Sets the csrftoken cookie and returns the token in the body.
    Still useful for any session-based admin flow; JWT consumers
    can skip this endpoint entirely.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "detail": "CSRF cookie set.",
                "csrfToken": get_token(request),
            }
        )


class CurrentUserView(APIView):
    """
    GET /api/users/me/

    Returns the authenticated user's profile. Works with both JWT
    (Authorization: Bearer) and session auth.
    """

    def get(self, request):
        return Response(AppUserSerializer(request.user).data)

from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import AppUserSerializer, LoginSerializer


@method_decorator(csrf_protect, name="dispatch")
class LoginView(APIView):
    """
    POST /api/users/login/

    Authenticates against Django's auth backend and starts a session.
    The browser receives a session cookie; no tokens are issued.

    DRF wraps APIViews in ``csrf_exempt`` and its ``SessionAuthentication``
    only enforces CSRF once a user is already authenticated, which would
    leave login itself open to login-CSRF. ``csrf_protect`` above restores
    the middleware check so anonymous POSTs must carry a valid token.
    """

    permission_classes = [AllowAny]

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
        login(request, user)
        return Response(AppUserSerializer(user).data)


class LogoutView(APIView):
    """POST /api/users/logout/ — ends the session."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    """
    GET /api/users/csrf/

    Sets the ``csrftoken`` cookie and also returns the token in the
    JSON body. The cookie is required for Django's CSRF middleware to
    validate subsequent POSTs, and the body copy lets a cross-origin
    frontend read the token directly — on a different origin it cannot
    read the backend's cookies via ``document.cookie``.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        return Response(
            {
                "detail": "CSRF cookie set.",
                "csrfToken": get_token(request),
            }
        )


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CurrentUserView(APIView):
    """
    GET /api/users/me/

    Doubles as a CSRF bootstrap endpoint: the React app calls this on load
    to (a) set the csrftoken cookie and (b) learn whether the user is
    currently signed in. Returns 401 if no session exists.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Not authenticated."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        return Response(AppUserSerializer(request.user).data)

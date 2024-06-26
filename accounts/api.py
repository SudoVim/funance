from django.urls import path
from django.contrib.auth import login
from knox.views import LoginView, LogoutView, LogoutAllView
from rest_framework import permissions, status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.generics import GenericAPIView
from rest_framework.authtoken.serializers import AuthTokenSerializer

from api.mixins import APIMixin

from .serializers import AccountSerializer


class LoginAPI(LoginView):
    """
    handler for logging in to the application
    """

    authentication_classes: list = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]

        login(request, user)
        return super().post(request, format=format)


class LogoutAPI(LogoutView, APIMixin):
    """
    handler for logging out of the application
    """


class LogoutAllAPI(LogoutAllView, APIMixin):
    """
    handler for logging all tokens out of the application
    """


class AccountHandler(GenericAPIView):
    """
    handler for querying the currently authenticated user
    """

    serializer_class = AccountSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request: Request) -> Response:
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)


urlpatterns = [
    path("login", LoginAPI.as_view()),
    path("logout", LogoutAPI.as_view()),
    path("logoutall", LogoutAllAPI.as_view()),
    path("account", AccountHandler.as_view()),
]

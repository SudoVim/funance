from django.urls import path
from django.contrib.auth import login
from knox.views import LoginView, LogoutView, LogoutAllView
from rest_framework import permissions, status
from rest_framework.authtoken.serializers import AuthTokenSerializer

from api.mixins import APIMixin


class LoginAPI(LoginView):
    """
    handler for logging in to the application
    """

    authentication_classes = []
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


urlpatterns = [
    path("login", LoginAPI.as_view()),
    path("logout", LogoutAPI.as_view()),
    path("logoutall", LogoutAllAPI.as_view()),
]

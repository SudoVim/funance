from django.urls import path
from django.contrib.auth import login
from knox.views import LoginView
from rest_framework import permissions, status
from rest_framework.authtoken.serializers import AuthTokenSerializer

class LoginAPI(LoginView):
    """
        handler for logging in to the application
    """
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, format=None):
        serializer = AuthTokenSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']

        login(request, user)
        return super().post(request, format=format)

urlpatterns = [
    path('login', LoginAPI.as_view()),
]

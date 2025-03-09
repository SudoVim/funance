from knox.auth import TokenAuthentication
from rest_framework import permissions


class APIMixin:
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

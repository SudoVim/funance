from rest_framework import permissions
from knox.auth import TokenAuthentication

class APIMixin():
    authentication_classes = [TokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

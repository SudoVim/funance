from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from .serializers import FundSerializer


class FundViewSet(viewsets.ModelViewSet):
    """
    View and edit funds
    """

    serializer_class = FundSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.funds.all()

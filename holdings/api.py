from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated

from .serializers import HoldingAccountSerializer


class HoldingAccountViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    View and edit holding accounts
    """

    serializer_class = HoldingAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.holding_accounts.order_by('name').all()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

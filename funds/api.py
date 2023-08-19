from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import BaseRouter

from .serializers import FundSerializer


class FundViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    View and edit funds
    """

    serializer_class = FundSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return self.request.user.funds.order_by("name").all()

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


def register_routes(router: BaseRouter):
    router.register(r"funds", FundViewSet, basename="fund")

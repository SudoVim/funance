from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import BaseRouter
from rest_framework.decorators import action
from rest_framework.response import Response

from tickers.models import Ticker
from .serializers import (
    FundSerializer,
    CreateFundAllocationSerializer,
    FundAllocationSerializer,
)


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

    @action(detail=True, methods=["post"])
    def create_allocation(self, request, pk=None):
        """
        Create and return a new allocation for the specified fund
        """
        fund = self.get_object()
        serializer = CreateFundAllocationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ticker, _ = Ticker.objects.get_or_create(
            symbol=serializer.validated_data["ticker"]
        )
        return Response(
            FundAllocationSerializer(
                serializer.save(fund=fund, ticker=ticker),
                context={"request": request},
            ).data,
        )


def register_routes(router: BaseRouter):
    router.register(r"funds", FundViewSet, basename="fund")

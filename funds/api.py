from rest_framework import mixins, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.routers import BaseRouter
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.settings import api_settings

from tickers.models import Ticker
from .serializers import (
    FundSerializer,
    CreateFundAllocationSerializer,
    FundAllocationSerializer,
)
from .models import FundAllocation


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

    @action(detail=True, methods=["get"])
    def allocations(self, request, pk=None):
        """
        List fund allocations for a fund
        """
        fund = self.get_object()
        paginator = api_settings.DEFAULT_PAGINATION_CLASS()
        page = paginator.paginate_queryset(
            fund.allocations.order_by("ticker__symbol"),
            request,
        )
        serializer = FundAllocationSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class FundAllocationViewSet(
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    View and edit fund allocations
    """

    serializer_class = FundAllocationSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            FundAllocation.objects.filter(fund__owner=self.request.user)
            .order_by("ticker__symbol")
            .all()
        )


def register_routes(router: BaseRouter):
    router.register(r"funds", FundViewSet, basename="fund")
    router.register(r"fund_allocations", FundViewSet, basename="fundallocation")

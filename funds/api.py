from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.routers import BaseRouter
from rest_framework.serializers import BaseSerializer
from typing_extensions import override

from funance.utils.pagination import get_paginator
from tickers.models import Ticker

from .models import Fund, FundAllocation
from .serializers import (
    CreateFundAllocationSerializer,
    FundAllocationSerializer,
    FundSerializer,
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

    @override
    def get_queryset(self) -> QuerySet[Fund]:
        return Fund.objects.filter(owner=self.request.user).order_by("name").all()

    @override
    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def create_allocation(self, request: Request) -> Response:
        """
        Create and return a new allocation for the specified fund
        """
        fund = self.get_object()
        serializer = CreateFundAllocationSerializer(data=request.data)
        _ = serializer.is_valid(raise_exception=True)
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
    def allocations(self, request: Request) -> Response:
        """
        List fund allocations for a fund
        """
        fund = self.get_object()
        paginator = get_paginator()
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

    @override
    def get_queryset(self) -> QuerySet[FundAllocation]:
        return (
            FundAllocation.objects.filter(fund__owner=self.request.user)
            .order_by("ticker__symbol")
            .all()
        )


def register_routes(router: BaseRouter):
    router.register(r"funds", FundViewSet, basename="fund")
    router.register(r"fund_allocations", FundViewSet, basename="fundallocation")

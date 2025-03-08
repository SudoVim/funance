from typing import Any

from django.db.models import QuerySet
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.routers import BaseRouter
from rest_framework.serializers import BaseSerializer
from typing_extensions import override

from tickers.models import Ticker

from .models import HoldingAccount, HoldingAccountPurchase
from .serializers import (
    CreateHoldingAccountPurchaseSerializer,
    HoldingAccountPurchaseRequestSerializer,
    HoldingAccountPurchaseSerializer,
    HoldingAccountSerializer,
)


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

    @override
    def get_queryset(self) -> QuerySet[HoldingAccount]:
        return (
            HoldingAccount.objects.filter(
                owner=self.request.user,
            )
            .order_by("name")
            .all()
        )

    @override
    def perform_create(self, serializer: BaseSerializer) -> None:
        serializer.save(owner=self.request.user)

    @action(detail=True, methods=["post"])
    def create_purchase(self, request: Request, pk: Any = None):
        """
        Create and return a new purchase for the specified holding account
        """
        ha = self.get_object()
        serializer = CreateHoldingAccountPurchaseSerializer(data=request.data)
        _ = serializer.is_valid(raise_exception=True)
        ticker, _ = Ticker.objects.get_or_create(
            symbol=serializer.validated_data["ticker"]
        )
        return Response(
            HoldingAccountPurchaseSerializer(
                serializer.save(holding_account=ha, ticker=ticker),
                context={"request": request},
            ).data,
        )


class HoldingAccountPurchaseViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """
    Interact with holding account purchases
    """

    serializer_class = HoldingAccountPurchaseSerializer
    permission_classes = [IsAuthenticated]

    @override
    def get_queryset(self) -> QuerySet[HoldingAccountPurchase]:
        return (
            HoldingAccountPurchase.objects.filter(
                holding_account__owner=self.request.user
            )
            .order_by("-purchased_at")
            .all()
        )

    @override
    def filter_queryset(
        self, queryset: QuerySet[HoldingAccountPurchase]
    ) -> QuerySet[HoldingAccountPurchase]:
        serializer = HoldingAccountPurchaseRequestSerializer(
            data=self.request.query_params
        )
        _ = serializer.is_valid()

        holding_account_pk = serializer.validated_data.get("holding_account")
        if holding_account_pk:
            queryset = queryset.filter(holding_account__pk=holding_account_pk)

        ticker_symbol = serializer.validated_data.get("ticker")
        if ticker_symbol:
            queryset = queryset.filter(ticker__pk=ticker_symbol)

        return queryset


def register_routes(router: BaseRouter):
    router.register(
        "holding_accounts", HoldingAccountViewSet, basename="holdingaccount"
    )
    router.register(
        "holding_account_purchases",
        HoldingAccountPurchaseViewSet,
        basename="holdingaccountpurchase",
    )

from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from typing_extensions import override

from django_helpers.admin import DHModelAdmin, DHModelTabularInline
from funds.models import Fund
from funds.portfolio.models import Portfolio
from funds.portfolio.portfolio import reset_shares_to_value, update_tickers
from holdings.models import HoldingAccount
from tickers.models import Ticker
from tickers.tickers import query_daily, query_info


class HoldingAccountInline(DHModelTabularInline[HoldingAccount]):
    model = HoldingAccount
    fields = (
        "name",
        "number",
    )
    readonly_fields = fields
    extra = 0
    show_change_link = True

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccount]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related(*HoldingAccount.Prefetch.AvailableCash)
        )


class FundInline(DHModelTabularInline[Fund]):
    model = Fund
    fields = (
        "name",
        "active_version",
        "position_value|dollars",
        "position_percentage|percent",
        "portfolio_shares",
        "portfolio_percentage|percent",
        "budget|dollars",
    )
    readonly_fields = fields
    extra = 0
    show_change_link = True

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[Fund]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                *Fund.Prefetch.PositionValue,
            )
        )


@admin.register(Portfolio)
class PortfolioAdmin(DHModelAdmin[Portfolio]):
    inlines = (
        HoldingAccountInline,
        FundInline,
    )
    readonly_fields = (
        "total_value|dollars",
        "available_cash|dollars",
        "cash_percent|percent",
        "cash_shares",
        "position_value|dollars",
        "action_buttons",
    )
    change_actions = ("update_tickers", "reset_shares_to_value")

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[Portfolio]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                *(Portfolio.Prefetch.AvailableCash | Portfolio.Prefetch.PositionValue)
            )
        )

    def update_tickers(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        update_tickers(obj)
        return self.redirect_referrer(request)

    def reset_shares_to_value(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        reset_shares_to_value(obj)
        return self.redirect_referrer(request)

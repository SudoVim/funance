import datetime
from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html_join
from typing_extensions import override

from django_helpers.admin import DHModelAdmin, DHModelTabularInline
from django_helpers.links import get_admin_list_url
from django_helpers.prefetch import prefetch
from funds.funds import activate, create_new_version
from funds.models import Fund
from funds.portfolio.models import Portfolio, PortfolioWeek
from funds.portfolio.performance import sync_performance_weeks
from funds.portfolio.portfolio import (
    apply_suggestions,
    reset_shares_to_value,
    update_tickers,
)
from holdings.models import (
    HoldingAccount,
    HoldingAccountAction,
    HoldingAccountGeneration,
    HoldingAccountSale,
)


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
        "budget_delta|dollars",
        "suggested_portfolio_shares|number",
        "suggested_portfolio_change|number",
        "suggested_portfolio_change_percent|percent",
        "suggested_portfolio_change_value|dollars",
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
                *(
                    Fund.Prefetch.PositionValue
                    | Fund.Prefetch.PositionPercentage
                    | prefetch(
                        "portfolio",
                        Portfolio.Prefetch.AvailableCash
                        | Portfolio.Prefetch.PositionValue
                        | Portfolio.Prefetch.PositionPercentage,
                    )
                )
            )
            .order_by("-active_version__portfolio_shares")
        )


@admin.register(Portfolio)
class PortfolioAdmin(DHModelAdmin[Portfolio]):
    inlines = (
        HoldingAccountInline,
        FundInline,
    )
    readonly_fields = (
        "total_value|dollars",
        "portfolio_confidence_percentage|percent",
        "cash_confidence_percentage|percent",
        "available_cash|dollars",
        "cash_percent|percent",
        "cash_shares|number",
        "suggested_cash_shares|number",
        "suggested_cash_change_percentage|percent",
        "suggested_cash_change_amount|dollars",
        "cash_budget_delta|dollars",
        "position_value|dollars",
        "performance",
        "action_buttons",
    )
    change_actions = (
        "update_tickers",
        "reset_shares_to_value",
        "create_new_versions",
        "apply_portfolio_suggestions",
        "sync_performance",
    )

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[Portfolio]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                *(
                    Portfolio.Prefetch.AvailableCash
                    | Portfolio.Prefetch.PositionValue
                    | Portfolio.Prefetch.PositionPercentage
                )
            )
        )

    def performance(self, obj: HoldingAccount) -> str:
        return format_html_join(
            " | ",
            "{}",
            [
                [
                    self.generate_link(
                        get_admin_list_url(
                            PortfolioWeek,
                            {"portfolio__id__exact": obj.pk},
                        ),
                        "Weekly",
                    )
                ],
            ],
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

    def create_new_versions(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        for fund in obj.funds.all():
            if not fund.active_version:
                continue
            new_version = create_new_version(fund.active_version)
            activate(new_version)
        return self.redirect_referrer(request)

    def sync_performance(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        sync_performance_weeks.delay(obj)
        return self.redirect_referrer(request)

    def apply_portfolio_suggestions(
        self, request: HttpRequest, pk: Any
    ) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        apply_suggestions(obj)
        return self.redirect_referrer(request)


@admin.register(PortfolioWeek)
class PortfolioWeekAdmin(DHModelAdmin[PortfolioWeek]):
    list_display = (
        "date",
        "portfolio",
        "sale_profit|dollars",
        "sale_interest|percent",
        "generation_profit|dollars",
        "total_profit|dollars",
        "net_cost_basis|dollars",
    )
    readonly_fields = ("links",)

    def links(self, obj: PortfolioWeek) -> str:
        return format_html_join(
            " | ",
            "{}",
            [
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountAction,
                            {
                                "position__holding_account__portfolio__id__exact": obj.portfolio.pk,
                                "purchased_on__gte": obj.date.strftime("%Y-%m-%d"),
                                "purchased_on__lt": (
                                    obj.date + datetime.timedelta(days=7)
                                ).strftime("%Y-%m-%d"),
                            },
                        ),
                        "Actions",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountSale,
                            {
                                "position__holding_account__portfolio__id__exact": obj.portfolio.pk,
                                "sale_date__gte": obj.date.strftime("%Y-%m-%d"),
                                "sale_date__lt": (
                                    obj.date + datetime.timedelta(days=7)
                                ).strftime("%Y-%m-%d"),
                            },
                        ),
                        "Sales",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountGeneration,
                            {
                                "position__holding_account__portfolio__id__exact": obj.portfolio.pk,
                                "date__gte": obj.date.strftime("%Y-%m-%d"),
                                "date__lt": (
                                    obj.date + datetime.timedelta(days=7)
                                ).strftime("%Y-%m-%d"),
                            },
                        ),
                        "Generations",
                    )
                ],
            ],
        )

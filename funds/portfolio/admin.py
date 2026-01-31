import datetime
from decimal import Decimal
from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html_join
from typing_extensions import override

from django_helpers.admin import DHModelAdmin, DHModelTabularInline
from django_helpers.admin_filters import format_dollars, format_percent
from django_helpers.links import get_admin_change_url, get_admin_list_url
from django_helpers.prefetch import prefetch
from funds.models import Fund, FundVersion
from funds.portfolio.models import Portfolio, PortfolioVersion, PortfolioWeek
from funds.portfolio.performance import sync_performance_weeks
from funds.portfolio.portfolio import (
    apply_suggestions,
    create_new_versions,
    reset_shares_to_value,
    update_tickers,
    update_version_end_value,
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
        "available_cash|dollars",
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
        # FundInline,
    )
    readonly_fields = (
        "total_value|dollars",
        "available_cash|dollars",
        "position_value|dollars",
        # "portfolio_confidence_percentage|percent",
        # "cash_confidence_percentage|percent",
        "cash_percent|percent",
        "cash_shares|number",
        # "suggested_cash_shares|number",
        # "suggested_cash_change_percentage|percent",
        # "suggested_cash_change_amount|dollars",
        # "cash_budget_delta|dollars",
        "performance",
        "links",
        "action_buttons",
    )
    change_actions = (
        "update_tickers",
        "sync_performance",
        "create_new_versions",
        "reset_shares_to_value",
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

    def performance(self, obj: Portfolio) -> str:
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

    def links(self, obj: Portfolio) -> str:
        def iterate_links():
            if obj.active_version:
                yield [
                    self.generate_link(
                        get_admin_change_url(obj.active_version),
                        "Active version",
                    ),
                ]
            yield [
                self.generate_link(
                    get_admin_list_url(
                        PortfolioVersion,
                        {"portfolio__id__exact": obj.pk},
                    ),
                    "All versions",
                )
            ]

        return format_html_join(
            " | ",
            "{}",
            list(iterate_links()),
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
        new_portfolio_version = create_new_versions(obj)
        return self.redirect_change_model(new_portfolio_version)

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


class FundVersionInline(DHModelTabularInline[FundVersion]):
    model = FundVersion
    fields = (
        "fund",
        "start_value|dollars",
        "current_value|dollars",
        "budget|dollars",
        "budget_percent|percent",
        "change_percent|percent",
        "change|dollars",
        "portfolio_shares",
        "portfolio_modifier",
        "confidence_percentage|percent",
        "suggested_portfolio_change",
        "suggested_portfolio_change_percent|percent",
        "suggested_portfolio_change_value|dollars",
        "total_change|dollars",
    )
    readonly_fields = (
        "fund",
        "start_value|dollars",
        "current_value|dollars",
        "budget|dollars",
        "budget_percent|percent",
        "change_percent|percent",
        "change|dollars",
        "confidence_percentage|percent",
        "suggested_portfolio_change",
        "suggested_portfolio_change_percent|percent",
        "suggested_portfolio_change_value|dollars",
        "total_change|dollars",
    )
    extra = 0
    show_change_link = True

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[FundVersion]:
        return (
            super()
            .get_queryset(request)
            .order_by("-start_value")
            .prefetch_related(
                *(
                    FundVersion.Prefetch.PositionValue
                    | FundVersion.Prefetch.PositionPercentage
                    | prefetch(
                        "portfolio_version",
                        prefetch("portfolio", Portfolio.Prefetch.AvailableCash)
                        | prefetch(
                            "fund_versions",
                            FundVersion.Prefetch.PositionValue
                            | FundVersion.Prefetch.PositionPercentage,
                        ),
                    )
                )
            )
        )

    def current_value(self, obj: FundVersion) -> Decimal:
        return obj.position_value

    def budget_percent(self, obj: FundVersion) -> Decimal:
        if obj.portfolio_version is None:
            return Decimal("0")
        return obj.budget / obj.portfolio_version.start_budget

    def change_percent(self, obj: FundVersion) -> Decimal:
        return obj.budget_delta_percent

    def change(self, obj: FundVersion) -> Decimal | None:
        return obj.budget_delta

    def total_change(self, obj: FundVersion) -> Decimal:
        return obj.budget_delta + obj.suggested_portfolio_change_value


@admin.register(PortfolioVersion)
class PortfolioVersionAdmin(DHModelAdmin[PortfolioVersion]):
    list_display = (
        "created_at",
        "portfolio",
        "started_at",
        "ended_at",
        "active",
        "start_value|dollars",
        "end_value|dollars",
        "change_value|dollars",
        "change_percent|percent",
    )
    readonly_fields = (
        "created_at",
        "updated_at",
        "portfolio",
        "parent",
        "active",
        "started_at",
        "ended_at",
        "values",
        "fund_values",
        "change",
        "per_share|dollars",
        "links",
        "action_buttons",
    )
    change_actions = ("apply_portfolio_suggestions",)
    inlines = (FundVersionInline,)

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[PortfolioVersion]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                *(
                    prefetch("portfolio", Portfolio.Prefetch.AvailableCash)
                    | prefetch(
                        "fund_versions",
                        FundVersion.Prefetch.PositionValue
                        | FundVersion.Prefetch.PositionPercentage,
                    )
                )
            )
        )

    def values(self, obj: PortfolioVersion) -> str:
        def iterate_rows():
            yield [
                "Cash",
                format_dollars(obj.start_cash),
                format_dollars(obj.current_cash),
                format_dollars(obj.end_cash),
                "--"
                if obj.start_cash is None
                else format_percent(obj.current_cash / obj.start_cash - 1),
                "--"
                if obj.start_cash is None
                else format_dollars(obj.current_cash - obj.start_cash),
            ]
            yield [
                "Positions",
                format_dollars(obj.start_value),
                format_dollars(obj.current_value),
                format_dollars(obj.end_value),
                "--"
                if obj.start_value is None
                else format_percent(obj.current_value / obj.start_value - 1),
                "--"
                if obj.start_value is None
                else format_dollars(obj.current_value - obj.start_value),
            ]
            yield [
                "Total",
                format_dollars(obj.start_budget),
                format_dollars(obj.current_budget),
                format_dollars(obj.end_budget),
                format_percent(obj.current_budget / obj.start_budget - 1),
                format_dollars(obj.current_budget - obj.start_budget),
            ]

        return self.generate_table(
            [
                "Type",
                "Start",
                "Current",
                "End",
                "Change %",
                "Change $",
            ],
            list(iterate_rows()),
        )

    def fund_values(self, obj: PortfolioVersion) -> str:
        def iterate_fund_row(fund_version: FundVersion):
            yield fund_version.fund.name
            yield format_dollars(fund_version.start_value)

            current_value = fund_version.end_value or fund_version.position_value
            yield format_dollars(current_value)

            if fund_version.end_value is None:
                yield "--"
            else:
                yield format_dollars(fund_version.start_value)

            if fund_version.start_value is None:
                yield "--"
                yield "--"
            else:
                yield format_percent(current_value / fund_version.start_value - 1)
                yield format_dollars(current_value - fund_version.start_value)

        def iterate_rows():
            fund_versions = obj.fund_versions.order_by("-start_value")
            for fund_version in fund_versions.all():
                yield list(iterate_fund_row(fund_version))

        return self.generate_table(
            [
                "Fund",
                "Start",
                "Current",
                "End",
                "Change %",
                "Change $",
            ],
            list(iterate_rows()),
        )

    def change(self, obj: PortfolioVersion) -> str:
        def iterate_rows():
            yield [
                "Cash",
                format_dollars(obj.start_cash),
                format_dollars(obj.current_cash),
                format_percent(obj.current_cash / obj.current_budget),
                format_dollars(obj.cash_budget),
                format_percent(obj.cash_budget / obj.current_cash - 1),
                format_dollars(obj.cash_budget - obj.current_cash),
                format_percent(1 - obj.portfolio_confidence_percentage),
                format_percent(obj.suggested_cash_change_percentage),
                format_dollars(obj.suggested_cash_change_amount),
                format_dollars(
                    obj.cash_budget
                    - obj.current_cash
                    + obj.suggested_cash_change_amount
                ),
            ]
            yield [
                "Positions",
                format_dollars(obj.start_value),
                format_dollars(obj.current_value),
                format_percent(obj.current_value / obj.current_budget),
                format_dollars(obj.position_budget),
                format_percent(obj.position_budget / obj.current_value - 1),
                format_dollars(obj.position_budget - obj.current_value),
                format_percent(obj.portfolio_confidence_percentage),
                format_percent(obj.suggested_portfolio_change_percentage),
                format_dollars(obj.suggested_portfolio_change_value),
                format_dollars(
                    obj.position_budget
                    - obj.current_value
                    + obj.suggested_portfolio_change_value
                ),
            ]

        return self.generate_table(
            [
                "Type",
                "Start",
                "Value",
                "Value %",
                "Budget",
                "Change %",
                "Change $",
                "Confidence",
                "Sugg. Ch %",
                "Sugg. Ch $",
                "Total Ch $",
            ],
            list(iterate_rows()),
        )

    def change_value(self, obj: PortfolioVersion) -> Decimal | None:
        return obj.change

    def per_share(self, obj: PortfolioVersion) -> Decimal:
        return obj.start_budget / obj.current_shares

    def links(self, obj: PortfolioVersion) -> str:
        def iterate_links():
            yield [
                self.generate_link(
                    get_admin_list_url(
                        FundVersion,
                        {
                            "portfolio_version__id__exact": obj.pk,
                        },
                    ),
                    "Fund Versions",
                )
            ]

        return format_html_join(
            " | ",
            "{}",
            list(iterate_links()),
        )

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

    def update_end_value(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        update_version_end_value(obj)
        return self.redirect_referrer(request)

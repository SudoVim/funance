from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html, format_html_join
from typing_extensions import override

import funds.portfolio.admin  # pyright: ignore[reportUnusedImport]
from django_helpers.admin import DHModelAdmin, DHModelTabularInline
from django_helpers.admin_filters import format_dollars, format_percent
from django_helpers.links import get_admin_list_url
from django_helpers.prefetch import prefetch
from funds.analytics import (
    allocation_changes,
    allocation_performance,
    format_when,
    version_return,
)
from funds.funds import (
    allocate_from_position,
    create_new_version,
    reset_portfolio_to_value,
)
from funds.models import Fund, FundVersion, FundVersionAllocation
from funds.portfolio.models import Portfolio
from funds.version_actions import apply_version_actions
from holdings.models import (
    HoldingAccountAction,
    HoldingAccountGeneration,
    HoldingAccountSale,
)


@admin.register(Fund)
class FundAdmin(DHModelAdmin[Fund]):
    list_display = (
        "name",
        "owner",
    )
    change_actions = ("create_root_version",)
    readonly_fields = (
        "active_version",
        "performance",
        "links",
        "action_buttons",
    )

    def performance(self, obj: Fund | None) -> str:
        if obj is None or obj.active_version is None:
            return "No active version."
        version = obj.active_version
        return self.generate_table(
            ["Start", "Current", "Gain loss", "Return since start"],
            [
                [
                    format_dollars(version.start_value),
                    format_dollars(version.current_value),
                    format_dollars(version.gain_loss),
                    format_percent(version.return_since_start),
                ]
            ],
        )

    def links(self, obj: Fund):
        return format_html_join(
            " | ",
            "{}",
            [
                [
                    self.generate_link(
                        get_admin_list_url(
                            FundVersion,
                            {"fund__id__exact": obj.pk},
                        ),
                        "Versions",
                    )
                ],
            ],
        )

    def create_root_version(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)
        return self.redirect_add_model(
            FundVersion,
            query_params={
                "fund": obj.pk,
            },
        )


class FundVersionAllocationInline(DHModelTabularInline[FundVersionAllocation]):
    model = FundVersionAllocation
    autocomplete_fields = ("ticker",)
    extra = 0
    fields = (
        "ticker",
        "weekly_confidence",
        "monthly_confidence",
        "quarterly_confidence",
        "position_confidence_percentage|percent",
        "position_value|dollars",
        "position_percentage|percent",
        "shares",
        "budget|dollars",
        "budget_delta|dollars",
        "budget_delta_shares",
        "return_since_start|percent",
        "drift|percent",
        "version_action",
        "modify_shares",
    )
    readonly_fields = (
        "position_value|dollars",
        "position_percentage|percent",
        "position_confidence_percentage|percent",
        "budget|dollars",
        "budget_delta|dollars",
        "budget_delta_shares",
        "return_since_start|percent",
        "drift|percent",
    )
    show_change_link = True

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[FundVersionAllocation]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related(
                *(
                    FundVersionAllocation.Prefetch.PositionPercentage
                    | FundVersionAllocation.Prefetch.PositionValue
                )
            )
            .order_by("-shares")
        )


class FundVersionChildrenInline(DHModelTabularInline[FundVersion]):
    model = FundVersion
    extra = 0
    verbose_name_plural = "children"


@admin.register(FundVersion)
class FundVersionAdmin(DHModelAdmin[FundVersion]):
    inlines = (FundVersionAllocationInline, FundVersionChildrenInline)
    fields = (
        "fund",
        "parent",
        "portfolio_version",
        "active",
        "budget|dollars",
        "budget_delta|dollars",
        "budget_delta_percent|percent",
        "share_value|dollars",
        "position_value|dollars",
        "confidence_percentage|percent",
        "remaining_shares",
        "portfolio_modifier",
        "portfolio_shares",
        "suggested_portfolio_shares|number",
        "suggested_portfolio_change|number",
        "suggested_portfolio_change_percent|percent",
        "suggested_portfolio_change_value|dollars",
        "shares",
        "confidence_shift_percentage",
        "current_value|dollars",
        "gain_loss|dollars",
        "return_since_start|percent",
        "allocation_performance",
        "compared_to_parent",
        "action_buttons",
    )
    change_actions = (
        "allocate_from_positions",
        "reset_portfolio_to_value",
        "apply_version_actions",
    )
    readonly_fields = (
        "parent",
        # "portfolio_version",
        "active",
        "budget|dollars",
        "budget_delta|dollars",
        "budget_delta_percent|percent",
        "share_value|dollars",
        "position_value|dollars",
        "confidence_percentage|percent",
        "remaining_shares",
        "suggested_portfolio_shares|number",
        "suggested_portfolio_change|number",
        "suggested_portfolio_change_percent|percent",
        "suggested_portfolio_change_value|dollars",
        "current_value|dollars",
        "gain_loss|dollars",
        "return_since_start|percent",
        "allocation_performance",
        "compared_to_parent",
        "action_buttons",
    )
    list_display = (
        "created_at",
        "fund",
        "active",
        "shares",
        "start_value|dollars",
        "end_value|dollars",
        "change|dollars",
        "change_percent|percent",
        "gain_loss|dollars",
        "return_since_start|percent",
    )

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[FundVersion]:
        return (
            super()
            .get_queryset(request)
            .order_by("-active", "-created_at")
            .prefetch_related(
                *(
                    FundVersion.Prefetch.PositionPercentage
                    | FundVersion.Prefetch.PositionValue
                    | FundVersion.Prefetch.PortfolioValue
                    | FundVersion.Prefetch.PortfolioPercentage
                    | prefetch(
                        "portfolio_version",
                        prefetch("portfolio", Portfolio.Prefetch.AvailableCash)
                        | prefetch(
                            "fund_versions",
                            FundVersion.Prefetch.PositionValue
                            | FundVersion.Prefetch.PositionPercentage,
                        ),
                    )
                ),
                "parent__allocations__ticker",
            )
        )

    @override
    def get_readonly_fields(
        self, request: HttpRequest, obj: FundVersion | None = None
    ) -> tuple[str, ...]:
        readonly_fields = super().get_readonly_fields(request, obj)
        if obj is None:
            return tuple(readonly_fields)
        return tuple(readonly_fields) + ("fund",)

    def remaining_shares(self, obj: FundVersion) -> int:
        allocated_shares = sum(a.shares for a in obj.allocations.all())
        return obj.shares - allocated_shares

    def allocate_from_positions(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)
        allocate_from_position(obj)
        return self.redirect_referrer(request)

    def create_new_version(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)
        return self.redirect_change_model(
            create_new_version(obj),
        )

    def reset_portfolio_to_value(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)
        reset_portfolio_to_value(obj)
        return self.redirect_referrer(request)

    def apply_version_actions(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)
        apply_version_actions(obj)
        return self.redirect_referrer(request)

    @override
    def save_model(
        self, request: HttpRequest, obj: FundVersion, form: Any, change: Any
    ):
        super().save_model(request, obj, form, change)
        if "active" in form.changed_data and obj.active:
            _ = obj.fund.versions.exclude(pk=obj.pk).update(
                active=False,
            )
            obj.fund.active_version = obj  # pyright: ignore[reportAttributeAccessIssue]
            obj.fund.save()

    def allocation_performance(self, obj: FundVersion | None) -> str:
        if obj is None or obj.pk is None:
            return "--"
        rows = allocation_performance(obj)
        if len(rows) == 0:
            return "No allocations."

        def iterate_rows():
            for row in rows:
                yield [
                    row.symbol,
                    format_dollars(row.start_value),
                    format_dollars(row.current_value),
                    format_dollars(row.gain_loss),
                    format_percent(row.return_since_start),
                    format_percent(row.contribution),
                    format_percent(row.target_weight),
                    format_percent(row.actual_weight),
                    format_percent(row.drift),
                ]

        return self.generate_table(
            [
                "Ticker",
                "Start",
                "Current",
                "Gain loss",
                "Return since start",
                "Contribution",
                "Target weight",
                "Actual weight",
                "Drift",
            ],
            iterate_rows(),
        )

    def compared_to_parent(self, obj: FundVersion | None) -> str:
        if obj is None or obj.pk is None:
            return "--"
        changes = allocation_changes(obj)
        if changes is None or obj.parent is None:
            return "No previous version."

        def iterate_summary():
            for label, version in (
                ("Previous", obj.parent),
                ("This version", obj),
            ):
                if version is None:
                    continue
                summary = version_return(version)
                yield [
                    label,
                    format_when(summary.started_at),
                    format_dollars(summary.start_value),
                    format_dollars(summary.current_value),
                    format_dollars(summary.gain_loss),
                    format_percent(summary.return_since_start),
                ]

        def iterate_changes():
            for change in changes:
                yield [
                    change.symbol,
                    change.previous_shares,
                    change.shares,
                    change.share_change,
                    format_percent(change.previous_weight),
                    format_percent(change.weight),
                    format_percent(change.weight_change),
                    format_percent(change.previous_return),
                    format_percent(change.return_since_start),
                ]

        return format_html(
            "{}<br><br>{}",
            self.generate_table(
                [
                    "Version",
                    "Started",
                    "Start",
                    "Current",
                    "Gain loss",
                    "Return since start",
                ],
                iterate_summary(),
            ),
            self.generate_table(
                [
                    "Ticker",
                    "Prev shares",
                    "Shares",
                    "Share change",
                    "Prev weight",
                    "Weight",
                    "Weight change",
                    "Prev return",
                    "Return",
                ],
                iterate_changes(),
            ),
        )


@admin.register(FundVersionAllocation)
class FundVersionAllocationAdmin(DHModelAdmin[FundVersionAllocation]):
    readonly_fields = (
        "version",
        "ticker",
        "position_value|dollars",
        "position_percentage|percent",
        "position_confidence_percentage|percent",
        "budget|dollars",
        "budget_delta|dollars",
        "budget_delta_shares",
        "start_value|dollars",
        "end_value|dollars",
        "current_value|dollars",
        "gain_loss|dollars",
        "return_since_start|percent",
        "contribution|percent",
        "target_weight|percent",
        "actual_weight|percent",
        "drift|percent",
        "latest_sale_date",
        "links",
    )

    def links(self, obj: FundVersionAllocation) -> str:
        return format_html_join(
            " | ",
            "{}",
            [
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountAction,
                            {"position__ticker__symbol": obj.ticker.pk},
                        ),
                        "Actions",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountAction,
                            {
                                "position__ticker__symbol": obj.ticker.pk,
                                "has_remaining_quantity__exact": "1",
                                "o": "1",
                            },
                        ),
                        "Available",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountSale,
                            {"position__ticker__symbol": obj.ticker.pk},
                        ),
                        "Sales",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountGeneration,
                            {"position__ticker__symbol": obj.ticker.pk},
                        ),
                        "Generations",
                    )
                ],
            ],
        )

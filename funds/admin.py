from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html_join
from typing_extensions import override

import funds.portfolio.admin  # pyright: ignore[reportUnusedImport]
from django_helpers.admin import DHModelAdmin, DHModelTabularInline
from django_helpers.links import get_admin_list_url
from funds.funds import (
    activate,
    allocate_from_position,
    apply_suggestions,
    create_new_version,
)
from funds.models import Fund, FundVersion, FundVersionAllocation


@admin.register(Fund)
class FundAdmin(DHModelAdmin[Fund]):
    list_display = (
        "name",
        "owner",
    )
    change_actions = ("create_root_version",)
    readonly_fields = (
        "active_version",
        "links",
        "action_buttons",
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
        "position_value|dollars",
        "position_percentage|percent",
        "modifier",
        "shares",
        "suggested_shares|number",
        "suggested_change_percent|percent",
        "suggested_change|dollars",
        "budget|dollars",
        "budget_delta|dollars",
        "budget_delta_shares",
    )
    readonly_fields = (
        "position_value|dollars",
        "position_percentage|percent",
        "suggested_shares|number",
        "suggested_change_percent|percent",
        "suggested_change|dollars",
        "budget|dollars",
        "budget_delta|dollars",
        "budget_delta_shares",
    )

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
        "active",
        "budget|dollars",
        "budget_delta|dollars",
        "budget_delta_percent|percent",
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
        "action_buttons",
    )
    change_actions = (
        "allocate_from_positions",
        "create_new_version",
        "apply_suggestions",
        "activate",
    )
    readonly_fields = (
        "parent",
        "active",
        "budget|dollars",
        "budget_delta|dollars",
        "budget_delta_percent|percent",
        "position_value|dollars",
        "confidence_percentage|percent",
        "remaining_shares",
        "suggested_portfolio_shares|number",
        "suggested_portfolio_change|number",
        "suggested_portfolio_change_percent|percent",
        "suggested_portfolio_change_value|dollars",
        "action_buttons",
    )
    list_display = "created_at", "fund", "active", "shares"

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
                )
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

    def apply_suggestions(self, request: HttpRequest, pk: Any) -> HttpResponse:
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

    def activate(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)
        activate(obj)
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

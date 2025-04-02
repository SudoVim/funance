from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html_join
from typing_extensions import override

from django_helpers.admin import DHModelAdmin, DHModelTabularInline
from django_helpers.links import get_admin_list_url
from funds.funds import allocate_from_position
from funds.models import Fund, FundVersion, FundVersionAllocation, Portfolio
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
        "available_cash|dollars",
        "cash_percent|percent",
        "position_value|dollars",
        "action_buttons",
    )
    change_actions = ("update_tickers",)

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

        tickers = Ticker.objects.filter(
            holding_account_positions__holding_account__portfolio=obj,
        )
        for ticker in tickers.iterator():
            query_info.delay(ticker)
            query_daily.delay(ticker)
        return self.redirect_referrer(request)


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


@admin.register(FundVersion)
class FundVersionAdmin(DHModelAdmin[FundVersion]):
    inlines = (FundVersionAllocationInline,)
    change_actions = ("allocate_from_positions",)
    readonly_fields = (
        "parent",
        "remaining_shares",
        "action_buttons",
    )
    list_display = "created_at", "fund", "active", "shares"

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[FundVersion]:
        return super().get_queryset(request).order_by("-active", "-created_at")

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

import datetime
from decimal import Decimal
from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html_join
from typing_extensions import override

from django_helpers.admin import DHModelAdmin
from django_helpers.links import get_admin_list_url
from holdings.account import parse_positions, sync_positions
from holdings.models import (
    HoldingAccount,
    HoldingAccountAction,
    HoldingAccountAlias,
    HoldingAccountDocument,
    HoldingAccountGeneration,
    HoldingAccountPosition,
    HoldingAccountSale,
)


class HoldingAccountAliasInline(admin.TabularInline[HoldingAccountAlias]):
    model = HoldingAccountAlias
    extra = 0


class HoldingAccountDocumentInline(admin.TabularInline[HoldingAccountDocument]):
    model = HoldingAccountDocument
    extra = 0
    fields = "order", "document_type", "document"

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountDocument]:
        return super().get_queryset(request).order_by("order", "created_at")


@admin.register(HoldingAccount)
class HoldingAccountAdmin(DHModelAdmin[HoldingAccount]):
    inlines = (
        HoldingAccountAliasInline,
        HoldingAccountDocumentInline,
    )
    readonly_fields = ("links", "action_buttons")
    change_actions = (
        "reset_positions",
        "parse_positions",
    )

    def links(self, obj: HoldingAccount) -> str:
        return format_html_join(
            " | ",
            "{}",
            [
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountDocument,
                            {"holding_account__id__exact": obj.pk},
                        ),
                        "Documents",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountPosition,
                            {"holding_account__id__exact": obj.pk},
                        ),
                        "Positions",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountAction,
                            {"position__holding_account__id__exact": obj.pk},
                        ),
                        "Actions",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountSale,
                            {"position__holding_account__id__exact": obj.pk},
                        ),
                        "Sales",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountGeneration,
                            {"position__holding_account__id__exact": obj.pk},
                        ),
                        "Generations",
                    )
                ],
            ],
        )

    def reset_positions(self, request: HttpRequest, pk: Any) -> HttpResponse:
        """
        Parse positions represented in the attached documents.
        """
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        _ = obj.positions.all().delete()
        return self.redirect_referrer(request)

    def parse_positions(self, request: HttpRequest, pk: Any) -> HttpResponse:
        """
        Parse positions represented in the attached documents.
        """
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found.",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        positions = parse_positions(obj)
        sync_positions(obj, positions)
        return self.redirect_referrer(request)


@admin.register(HoldingAccountDocument)
class HoldingAccountDocumentAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("__str__", "holding_account", "document_type", "created_at")


class HasPositionFilter(admin.SimpleListFilter):
    title = "Has position"
    parameter_name = "has_position"

    @override
    def lookups(self, request: HttpRequest, model_admin: "HoldingAccountPositionAdmin"):
        return [
            ("has_position", "Has position"),
            ("all_positions", "All positions"),
        ]

    @override
    def queryset(
        self, request: HttpRequest, queryset: QuerySet[HoldingAccountPosition]
    ) -> QuerySet[HoldingAccountPosition]:
        if self.value() == "all_positions":
            return queryset
        return queryset.filter(quantity__gt=0)


@admin.register(HoldingAccountPosition)
class HoldingAccountPositionAdmin(DHModelAdmin[HoldingAccountPosition]):
    list_filter = (HasPositionFilter, "holding_account")
    search_fields = ("ticker_symbol", "ticker__symbol")
    autocomplete_fields = ("ticker",)
    readonly_fields = (
        "holding_account",
        "links",
        "ticker_symbol",
        "total_sale_profit|dollars",
        "total_sale_interest|percent",
        "total_generation_profit|dollars",
        "generation_frequency",
        "average_generation_interest|percent",
        "total_profit|dollars",
        "total_interest|percent",
        "total_available_profit|dollars",
        "total_available_interest|percent",
    )
    list_display = (
        "ticker_symbol",
        "holding_account",
        "quantity|number",
        "cost_basis|dollars",
        "total_sale_profit|dollars",
        "total_generation_profit|dollars",
        "total_profit|dollars",
        "total_available_profit|dollars",
    )

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountPosition]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related("sales", "generations", "actions")
            .order_by("ticker_symbol")
        )

    def links(self, obj: HoldingAccountPosition) -> str:
        return format_html_join(
            " | ",
            "{}",
            [
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountAction,
                            {"position__id__exact": obj.pk},
                        ),
                        "Actions",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountAction,
                            {
                                "position__id__exact": obj.pk,
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
                            {"position__id__exact": obj.pk},
                        ),
                        "Sales",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountGeneration,
                            {"position__id__exact": obj.pk},
                        ),
                        "Generations",
                    )
                ],
            ],
        )

    def total_available_profit(self, obj: HoldingAccountPosition) -> Decimal | None:
        if not obj.ticker or not obj.ticker.current_price:
            return None
        return obj.available_purchases.potential_profit(obj.ticker.current_price)

    def generation_frequency(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                str(obj.generation_frequency.quantize(Decimal("0.01"))),
                "/yr",
            ]
        )

    def total_available_interest(self, obj: HoldingAccountPosition) -> Decimal | None:
        if not obj.ticker or not obj.ticker.current_price:
            return None
        return obj.available_purchases.total_interest(obj.ticker.current_price)


@admin.register(HoldingAccountGeneration)
class HoldingAccountGenerationAdmin(DHModelAdmin[HoldingAccountGeneration]):
    list_filter = ("position__holding_account",)
    list_display = (
        "date",
        "event",
        "symbol",
        "amount|dollars",
        "cost_basis|dollars",
        "percentage|percent",
    )
    readonly_fields = (
        "amount|dollars",
        "cost_basis|dollars",
        "percentage|percent",
    )

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountGeneration]:
        return super().get_queryset(request).order_by("-date")

    def symbol(self, obj: HoldingAccountGeneration) -> str:
        return obj.position.ticker_symbol

    def amount(self, obj: HoldingAccountGeneration) -> Decimal:
        return obj.amount.quantize(Decimal("0.001"))

    def percentage(self, obj: HoldingAccountGeneration) -> Decimal:
        return obj.position_generation.position_percentage()

    @override
    def has_add_permission(
        self, request: HttpRequest, obj: HoldingAccountPosition | None = None
    ) -> bool:
        return False

    @override
    def has_change_permission(
        self, request: HttpRequest, obj: HoldingAccountGeneration | None = None
    ) -> bool:
        return False

    @override
    def has_delete_permission(
        self, request: HttpRequest, obj: HoldingAccountGeneration | None = None
    ) -> bool:
        return False


@admin.register(HoldingAccountAction)
class HoldingAccountActionAdmin(DHModelAdmin[HoldingAccountAction]):
    list_filter = ("position__holding_account", "has_remaining_quantity")
    list_display = (
        "purchased_on",
        "position__holding_account",
        "action",
        "price|dollars",
        "quantity|number",
        "remaining_quantity|number",
        "potential_profit|dollars",
        "potential_interest|percent",
    )

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountAction]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related("position__ticker")
            .order_by("-purchased_on")
        )

    def potential_profit(self, obj: HoldingAccountAction) -> Decimal | None:
        if obj.available_purchase is None:
            return None
        if obj.position.ticker and obj.position.ticker.current_price:
            return obj.available_purchase.potential_profit(
                obj.position.ticker.current_price
            ).quantize(Decimal("0.01"))

    def potential_interest(self, obj: HoldingAccountAction) -> Decimal | None:
        if obj.available_purchase is None:
            return None
        if obj.position.ticker and obj.position.ticker.current_price:
            return obj.available_purchase.potential_interest(
                datetime.date.today(),
                obj.position.ticker.current_price,
            ).quantize(Decimal("0.01"))


@admin.register(HoldingAccountSale)
class HoldingAccountSaleAdmin(DHModelAdmin[HoldingAccountSale]):
    list_filter = ("position__holding_account",)
    list_display = (
        "ticker_symbol",
        "quantity",
        "purchase_date",
        "purchase_price",
        "sale_date",
        "sale_price",
        "profit",
    )

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountSale]:
        return super().get_queryset(request).order_by("-sale_date")

    def ticker_symbol(self, obj: HoldingAccountSale) -> str:
        return obj.position.ticker_symbol

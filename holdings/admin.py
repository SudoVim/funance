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


class HoldingAccountPositionInline(admin.TabularInline[HoldingAccountPosition]):
    model = HoldingAccountPosition
    show_change_link = True
    extra = 0
    readonly_fields = (
        "ticker_symbol",
        "total_sale_profit",
        "average_sale_interest",
        "total_generation_profit",
        "generation_frequency",
        "average_generation_interest",
        "total_profit",
        "total_interest",
    )

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountPosition]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related("sales", "generations")
            .order_by("ticker_symbol")
        )

    def total_sale_profit(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                "$",
                str(obj.total_sale_profit.quantize(Decimal("0.01"))),
            ]
        )

    def total_generation_profit(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                "$",
                str(obj.total_generation_profit.quantize(Decimal("0.01"))),
            ]
        )

    def total_profit(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                "$",
                str(obj.total_profit.quantize(Decimal("0.01"))),
            ]
        )

    def average_sale_interest(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                str((obj.average_sale_interest * 100).quantize(Decimal("0.01"))),
                "%",
            ]
        )

    def generation_frequency(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                str(obj.generation_frequency.quantize(Decimal("0.01"))),
                "/yr",
            ]
        )

    def average_generation_interest(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                str((obj.average_generation_interest * 100).quantize(Decimal("0.01"))),
                "%",
            ]
        )

    def total_interest(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                str((obj.total_interest * 100).quantize(Decimal("0.01"))),
                "%",
            ]
        )


@admin.register(HoldingAccount)
class HoldingAccountAdmin(DHModelAdmin[HoldingAccount]):
    inlines = (
        HoldingAccountAliasInline,
        HoldingAccountDocumentInline,
        HoldingAccountPositionInline,
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
                            {"holding_account": obj.pk},
                        ),
                        "Documents",
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


class HoldingAccountSaleInline(admin.TabularInline[HoldingAccountSale]):
    model = HoldingAccountSale
    readonly_fields = "profit", "interest"

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountSale]:
        return super().get_queryset(request).order_by("-sale_date")

    def profit(self, obj: HoldingAccountSale) -> Decimal:
        return obj.position_sale.profit().quantize(Decimal("0.001"))

    def interest(self, obj: HoldingAccountSale) -> str:
        return "".join(
            [
                str((obj.position_sale.interest() * 100).quantize(Decimal("0.01"))),
                "%",
            ]
        )

    @override
    def has_add_permission(
        self, request: HttpRequest, obj: HoldingAccountPosition | None = None
    ) -> bool:
        return False

    @override
    def has_change_permission(
        self, request: HttpRequest, obj: HoldingAccountSale | None = None
    ) -> bool:
        return False

    @override
    def has_delete_permission(
        self, request: HttpRequest, obj: HoldingAccountSale | None = None
    ) -> bool:
        return False


class HoldingAccountGenerationInline(admin.TabularInline[HoldingAccountGeneration]):
    model = HoldingAccountGeneration
    readonly_fields = "amount", "percentage"

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountGeneration]:
        return super().get_queryset(request).order_by("-date")

    def amount(self, obj: HoldingAccountGeneration) -> Decimal:
        return obj.amount.quantize(Decimal("0.001"))

    def percentage(self, obj: HoldingAccountGeneration) -> str:
        return "".join(
            [
                str(
                    (obj.position_generation.position_percentage() * 100).quantize(
                        Decimal("0.01")
                    )
                ),
                "%",
            ]
        )

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


@admin.register(HoldingAccountPosition)
class HoldingAccountPositionAdmin(DHModelAdmin[HoldingAccountPosition]):
    list_filter = ("holding_account",)
    readonly_fields = (
        "holding_account",
        "ticker_symbol",
        "total_sale_profit",
        "average_sale_interest",
        "total_generation_profit",
        "generation_frequency",
        "average_generation_interest",
        "total_profit",
        "total_interest",
    )
    inlines = (HoldingAccountSaleInline, HoldingAccountGenerationInline)

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountPosition]:
        return (
            super()
            .get_queryset(request)
            .prefetch_related("sales", "generations")
            .order_by("ticker_symbol")
        )

    def total_sale_profit(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                "$",
                str(obj.total_sale_profit.quantize(Decimal("0.01"))),
            ]
        )

    def total_generation_profit(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                "$",
                str(obj.total_generation_profit.quantize(Decimal("0.01"))),
            ]
        )

    def total_profit(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                "$",
                str(obj.total_profit.quantize(Decimal("0.01"))),
            ]
        )

    def average_sale_interest(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                str((obj.average_sale_interest * 100).quantize(Decimal("0.01"))),
                "%",
            ]
        )

    def generation_frequency(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                str(obj.generation_frequency.quantize(Decimal("0.01"))),
                "/yr",
            ]
        )

    def average_generation_interest(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                str((obj.average_generation_interest * 100).quantize(Decimal("0.01"))),
                "%",
            ]
        )

    def total_interest(self, obj: HoldingAccountPosition) -> str:
        return "".join(
            [
                str((obj.total_interest * 100).quantize(Decimal("0.01"))),
                "%",
            ]
        )


@admin.register(HoldingAccountAction)
class HoldingAccountActionAdmin(DHModelAdmin[HoldingAccountAction]):
    list_filter = ("position__holding_account",)


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


@admin.register(HoldingAccountGeneration)
class HoldingAccountGenerationAdmin(DHModelAdmin[HoldingAccountGeneration]):
    list_filter = ("position__holding_account",)

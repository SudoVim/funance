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
    readonly_fields = ("ticker_symbol",)

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountPosition]:
        return super().get_queryset(request).order_by("ticker_symbol")


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


@admin.register(HoldingAccountPosition)
class HoldingAccountPositionAdmin(DHModelAdmin[HoldingAccountPosition]):
    list_filter = ("holding_account",)


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

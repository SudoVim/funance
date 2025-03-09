from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest
from django.utils.html import format_html_join
from typing_extensions import override

from django_helpers.admin import DHModelAdmin
from django_helpers.links import get_admin_list_url
from holdings.models import (
    HoldingAccount,
    HoldingAccountAlias,
    HoldingAccountDocument,
    HoldingAccountPurchase,
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
class HoldingAccountAdmin(DHModelAdmin):
    inlines = HoldingAccountAliasInline, HoldingAccountDocumentInline
    readonly_fields = ("links",)

    def links(self, obj: HoldingAccountPurchase) -> str:
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
                            HoldingAccountPurchase,
                            {"holding_account": obj.pk},
                        ),
                        "Purchases",
                    )
                ],
            ],
        )


@admin.register(HoldingAccountPurchase)
class HoldingAccountPurchaseAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = [
        "id",
        "account_name",
        "purchased_at",
        "ticker_symbol",
        "operation",
        "abs_quantity_value",
        "price_value",
    ]
    list_filter = ["holding_account"]


@admin.register(HoldingAccountDocument)
class HoldingAccountDocumentAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("__str__", "holding_account", "document_type", "created_at")

from django.contrib import admin

from holdings.models import (
    HoldingAccount,
    HoldingAccountDocument,
    HoldingAccountPurchase,
)


@admin.register(HoldingAccount)
class HoldingAccountAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    pass


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
    list_display = ("__str__", "created_at")

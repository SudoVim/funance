from django.contrib import admin

from holdings.models import (
    HoldingAccount,
    HoldingAccountDocument,
    HoldingAccountPurchase,
)


@admin.register(HoldingAccount)
class HoldingAccountAdmin(admin.ModelAdmin[HoldingAccount]):
    pass


@admin.register(HoldingAccountPurchase)
class HoldingAccountPurchaseAdmin(admin.ModelAdmin[HoldingAccountPurchase]):
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
class HoldingAccountDocumentAdmin(admin.ModelAdmin[HoldingAccountDocument]):
    list_display = ("__str__", "created_at")

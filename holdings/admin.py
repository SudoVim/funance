from typing import Any

from django.contrib import admin
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html_join
from typing_extensions import override

from django_helpers.admin import DHModelAdmin
from django_helpers.links import get_admin_list_url
from holdings.account import parse_positions, sync_actions
from holdings.models import (
    HoldingAccount,
    HoldingAccountAction,
    HoldingAccountAlias,
    HoldingAccountDocument,
    HoldingAccountPosition,
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
    change_actions = ("parse_positions",)

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
            ],
        )

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
        sync_actions(obj, positions)
        return self.redirect_referrer(request)


@admin.register(HoldingAccountDocument)
class HoldingAccountDocumentAdmin(admin.ModelAdmin):  # pyright: ignore[reportMissingTypeArgument]
    list_display = ("__str__", "holding_account", "document_type", "created_at")


class HoldingAccountActionInline(admin.TabularInline[HoldingAccountAction]):
    model = HoldingAccountAction
    extra = 0

    @override
    def get_queryset(self, request: HttpRequest) -> QuerySet[HoldingAccountAction]:
        return super().get_queryset(request).order_by("-purchased_on")

    @override
    def has_add_permission(self, request: HttpRequest, *args: Any) -> bool:
        return False

    @override
    def has_change_permission(
        self, request: HttpRequest, obj: HoldingAccountAction | None = None
    ) -> bool:
        return False

    @override
    def has_delete_permission(
        self, request: HttpRequest, obj: HoldingAccountAction | None = None
    ) -> bool:
        return False


@admin.register(HoldingAccountPosition)
class HoldingAccountPositionAdmin(DHModelAdmin[HoldingAccountPosition]):
    inlines = (HoldingAccountActionInline,)

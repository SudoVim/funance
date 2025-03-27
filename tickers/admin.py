import json
from decimal import Decimal
from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html

from django_helpers.admin import DHModelAdmin
from tickers.models import Ticker


@admin.register(Ticker)
class TickerAdmin(DHModelAdmin[Ticker]):
    search_fields = ["symbol"]
    change_actions = (
        "query_info",
        "query_daily",
    )
    readonly_fields = (
        "action_buttons",
        "latest_daily",
        "latest_info",
    )

    def latest_info(self, obj: Ticker) -> str:
        latest_info = obj.latest_info
        if latest_info is None:
            return "--"
        return format_html(
            "<pre>{}</pre>",
            json.dumps(
                latest_info.encode(),
                indent=2,
            ),
        )

    def latest_daily(self, obj: Ticker) -> str:
        latest_daily = obj.latest_daily
        if latest_daily is None:
            return "--"
        return format_html(
            "<pre>{}</pre>",
            json.dumps(
                latest_daily.encode(),
                indent=2,
            ),
        )

    def query_info(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        _ = obj.info.query()
        return self.redirect_referrer(request)

    def query_daily(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        obj.daily.query()
        latest = obj.daily.latest()
        if latest:
            obj.current_price = Decimal(latest.close)
            obj.save()
        return self.redirect_referrer(request)

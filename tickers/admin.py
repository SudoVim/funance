import json
from decimal import Decimal
from typing import Any

from django.contrib import admin
from django.http import HttpRequest, HttpResponse
from django.utils.html import format_html, format_html_join

from django_helpers.admin import DHModelAdmin
from django_helpers.links import get_admin_list_url
from holdings.models import (
    HoldingAccountAction,
    HoldingAccountGeneration,
    HoldingAccountPosition,
    HoldingAccountSale,
)
from tickers.models import Ticker
from tickers.tickers import query_daily, query_info


@admin.register(Ticker)
class TickerAdmin(DHModelAdmin[Ticker]):
    search_fields = ["symbol"]
    change_actions = ("query_latest",)
    readonly_fields = (
        "price|dollars",
        "links",
        "action_buttons",
        "latest_daily",
        "latest_info",
    )

    def links(self, obj: Ticker) -> str:
        return format_html_join(
            " | ",
            "{}",
            [
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountPosition,
                            {"ticker__symbol": obj.pk},
                        ),
                        "Positions",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountAction,
                            {"position__ticker__symbol": obj.pk},
                        ),
                        "Actions",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountAction,
                            {
                                "position__ticker__symbol": obj.pk,
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
                            {"position__ticker__symbol": obj.pk},
                        ),
                        "Sales",
                    )
                ],
                [
                    self.generate_link(
                        get_admin_list_url(
                            HoldingAccountGeneration,
                            {"position__ticker__symbol": obj.pk},
                        ),
                        "Generations",
                    )
                ],
            ],
        )

    def price(self, obj: Ticker) -> Decimal | None:
        latest_daily = obj.latest_daily
        if latest_daily is None:
            return None
        return Decimal(latest_daily.close)

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

    def query_latest(self, request: HttpRequest, pk: Any) -> HttpResponse:
        obj = self.get_object(request, pk)
        if not obj:
            self.message_user(
                request,
                "Object not found",
                level="ERROR",
            )
            return self.redirect_referrer(request)

        query_info.delay(obj)
        query_daily.delay(obj)
        return self.redirect_referrer(request)

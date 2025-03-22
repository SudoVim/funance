from django.contrib import admin

from django_helpers.admin import DHModelAdmin
from tickers.models import Ticker


@admin.register(Ticker)
class TickerAdmin(DHModelAdmin[Ticker]):
    search_fields = ["symbol"]

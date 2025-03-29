from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from django.utils.functional import cached_property
from typing_extensions import override

from funance_data.tickers.daily import TickerDaily, TickerDailyStore
from funance_data.tickers.info import TickerInfo, TickerInfoStore

TICKER_LENGTH = 10

if TYPE_CHECKING:
    from holdings.models import HoldingAccountPosition


class Ticker(models.Model):
    symbol = models.CharField(max_length=TICKER_LENGTH, primary_key=True, unique=True)

    holding_account_positions = models.QuerySet["HoldingAccountPosition"]

    @property
    def info(self) -> TickerInfoStore:
        """
        ticker info
        """
        return TickerInfoStore(str(self.symbol))

    @cached_property
    def latest_info(self) -> TickerInfo | None:
        return self.info.latest()

    @property
    def daily(self) -> TickerDailyStore:
        """
        daily price data for the given ticker
        """
        return TickerDailyStore(str(self.symbol))

    @cached_property
    def latest_daily(self) -> TickerDaily | None:
        return self.daily.latest()

    @property
    def price(self) -> Decimal | None:
        latest_daily = self.latest_daily
        if latest_daily is None:
            return None
        return Decimal(latest_daily.close)

    @override
    def __str__(self) -> str:
        return self.symbol

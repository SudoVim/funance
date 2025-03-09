from django.db import models

from funance_data.tickers.daily import TickerDailyStore
from funance_data.tickers.info import TickerInfoStore

TICKER_LENGTH = 10


class Ticker(models.Model):
    symbol = models.CharField(
        max_length=TICKER_LENGTH, primary_key=True, editable=False, unique=True
    )

    @property
    def info(self) -> TickerInfoStore:
        """
        ticker info
        """
        return TickerInfoStore(str(self.symbol))

    @property
    def daily(self) -> TickerDailyStore:
        """
        daily price data for the given ticker
        """
        return TickerDailyStore(str(self.symbol))

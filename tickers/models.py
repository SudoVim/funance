from django.db import models

from funance_data.tickers.info import TickerInfoStore
from funance_data.tickers.daily import TickerDailyStore


class Ticker(models.Model):
    symbol = models.CharField(
        max_length=10, primary_key=True, editable=False, unique=True
    )

    @property
    def info(self):
        """
        ticker info
        """
        return TickerInfoStore(self.symbol)  # type: ignore

    @property
    def daily(self):
        """
        daily price data for the given ticker
        """
        return TickerDailyStore(self.symbol)  # type: ignore

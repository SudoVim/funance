from django.db import models

from .ohlc import TickerOHLC

class Ticker(models.Model):
    symbol = models.CharField(max_length=10, primary_key=True, editable=False, unique=True)

    @property
    def ohlc(self):
        """
            ohlc data for the given ticker
        """
        return TickerOHLC(self.symbol)

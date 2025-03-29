from django_rq import job

from tickers.models import Ticker


@job("low")
def query_info(ticker: Ticker) -> None:
    """
    Query ticker info
    """
    _ = ticker.info.query()


@job("low")
def query_daily(ticker: Ticker) -> None:
    """
    Query ticker daily prices
    """
    ticker.daily.query()

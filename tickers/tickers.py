import datetime
from decimal import Decimal

import pytz
from django_rq import job
from django_rq.queues import get_scheduler

from tickers.models import Ticker


@job("low")
def query_info(ticker: Ticker) -> None:
    """
    Query ticker info
    """
    latest = ticker.info.latest()
    if latest is not None and latest.date >= datetime.date.today():
        return
    _ = ticker.info.query()


@job("low")
def query_daily(ticker: Ticker) -> None:
    """
    Query ticker daily prices
    """
    ticker.daily.query()
    _ = get_scheduler("default").enqueue_at(
        pytz.utc.localize(datetime.datetime.now()) + datetime.timedelta(seconds=5),
        update_price,
        ticker,
    )


@job("default")
def update_price(ticker: Ticker) -> None:
    latest_daily = ticker.latest_daily
    if latest_daily is None:
        ticker.current_price = Decimal("0")
        ticker.save()
        return
    ticker.current_price = Decimal(latest_daily.close)
    ticker.save()

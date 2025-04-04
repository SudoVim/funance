from django.db.models import prefetch_related_objects

from funds.portfolio.models import Portfolio
from tickers.models import Ticker
from tickers.tickers import query_daily, query_info


def update_tickers(self: Portfolio) -> None:
    tickers = Ticker.objects.filter(
        holding_account_positions__holding_account__portfolio=self,
    )
    for ticker in tickers.iterator():
        query_info.delay(ticker)
        query_daily.delay(ticker)


def reset_shares_to_value(self: Portfolio) -> None:
    prefetch_related_objects(
        [self],
        *(Portfolio.Prefetch.AvailableCash | Portfolio.Prefetch.PositionValue),
    )
    for fund in self.funds.all():
        if fund.active_version is None:
            continue
        fund.active_version.portfolio_shares = int(
            fund.active_version.position_percentage * self.shares
        )
        fund.active_version.save()

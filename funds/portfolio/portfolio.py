import datetime
from decimal import Decimal

import pytz
from django.db.models import prefetch_related_objects

from funds.funds import activate, create_new_version
from funds.models import FundVersion
from funds.portfolio.models import Portfolio, PortfolioVersion
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


def apply_suggestions(self: Portfolio) -> None:
    prefetch_related_objects(
        [self],
        *(Portfolio.Prefetch.AvailableCash | Portfolio.Prefetch.PositionValue),
    )

    def iterate_versions():
        for fund in self.funds.all():
            if fund.active_version is None:
                continue
            fund.active_version.portfolio_shares = (
                fund.active_version.suggested_portfolio_shares
            )
            yield fund.active_version

    _ = FundVersion.objects.bulk_update(
        iterate_versions(),
        fields=["portfolio_shares"],
    )


def create_new_versions(self: Portfolio) -> None:
    prefetch_related_objects(
        [self],
        *(Portfolio.Prefetch.AvailableCash | Portfolio.Prefetch.PositionValue),
    )

    now = pytz.utc.localize(datetime.datetime.now())
    new_portfolio_version = self.versions.create(
        parent=self.active_version,
        active=True,
        started_at=now,
    )
    for fund in self.funds.all():
        if not fund.active_version:
            continue
        new_version = create_new_version(fund.active_version, new_portfolio_version)
        activate(new_version)

    update_version_start_value(new_portfolio_version, save=False)
    update_version_start_cash(new_portfolio_version, save=False)
    new_portfolio_version.save(update_fields=["start_value", "start_cash"])

    if self.active_version:
        self.active_version.active = False
        self.active_version.ended_at = now
        update_version_end_value(self.active_version, save=False)
        update_version_end_cash(self.active_version, save=False)
        self.active_version.save(
            update_fields=[
                "active",
                "ended_at",
                "end_value",
                "end_cash",
            ]
        )

    self.active_version = new_portfolio_version
    self.save(update_fields=["active_version"])


def update_version_start_value(version: PortfolioVersion, save: bool = True) -> None:
    version.start_value = Decimal(
        sum(v.start_value for v in version.fund_versions.all() if v.start_value)
    )
    if save:
        version.save(update_fields=["start_value"])


def update_version_start_cash(version: PortfolioVersion, save: bool = True) -> None:
    version.start_cash = Decimal(
        sum(ha.available_cash for ha in version.portfolio.holding_accounts.all())
    )
    if save:
        version.save(update_fields=["start_cash"])


def update_version_end_value(version: PortfolioVersion, save: bool = True) -> None:
    """
    Update the :attr:`PortfolioVersion.end_value` of the given *version*.
    """
    version.end_value = Decimal(
        sum(
            Decimal(v.end_value or 0)
            for v in version.fund_versions.all()
            if v.end_value
        )
    )
    if save:
        version.save(update_fields=["end_value"])


def update_version_end_cash(version: PortfolioVersion, save: bool = True) -> None:
    version.end_cash = Decimal(
        sum(ha.available_cash for ha in version.portfolio.holding_accounts.all())
    )
    if save:
        version.save(update_fields=["end_cash"])

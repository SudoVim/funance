"""
Performance figures for portfolios, their versions, fund versions, and allocations.

The figures use each version's stored start and end snapshots together with
live position values. There is no daily value series, so this does not
reconstruct a path from trades or historical prices. A change in market value
also includes buys and sells made while that version was open.
"""

import datetime
from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal

from django.utils import timezone

from funds.models import FundVersion, FundVersionAllocation
from funds.portfolio.models import Portfolio, PortfolioVersion


@dataclass(frozen=True)
class AllocationPerformance:
    symbol: str
    start_value: Decimal | None
    current_value: Decimal
    gain_loss: Decimal | None
    return_since_start: Decimal | None
    contribution: Decimal | None
    target_weight: Decimal
    actual_weight: Decimal | None
    drift: Decimal | None


@dataclass(frozen=True)
class VersionReturn:
    started_at: datetime.datetime
    start_value: Decimal | None
    current_value: Decimal
    gain_loss: Decimal | None
    return_since_start: Decimal | None


@dataclass(frozen=True)
class AllocationChange:
    symbol: str
    previous_shares: int
    shares: int
    previous_weight: Decimal
    weight: Decimal
    previous_return: Decimal | None
    return_since_start: Decimal | None

    @property
    def share_change(self) -> int:
        return self.shares - self.previous_shares

    @property
    def weight_change(self) -> Decimal:
        return self.weight - self.previous_weight


@dataclass(frozen=True)
class ContributionRow:
    name: str
    start_value: Decimal | None
    current_value: Decimal | None
    gain_loss: Decimal | None
    return_since_start: Decimal | None
    contribution: Decimal | None


@dataclass(frozen=True)
class PortfolioVersionReturn:
    started_at: datetime.datetime | None
    ended_at: datetime.datetime | None
    active: bool
    start_budget: Decimal
    current_budget: Decimal
    gain_loss: Decimal | None
    return_since_start: Decimal | None


def format_when(value: datetime.datetime | None) -> str:
    if value is None:
        return "--"
    if timezone.is_aware(value):
        value = timezone.localtime(value)
    return value.strftime("%Y-%m-%d %H:%M")


def allocation_performance(version: FundVersion) -> list[AllocationPerformance]:
    """
    One row per allocation, largest gain first.

    Contribution is that allocation's gain divided by the fund version's
    starting value, so the rows sum to the fund's return since start when
    every allocation has a start snapshot.
    """

    def iterate_rows():
        for allocation in version.allocations.all():
            yield _allocation_performance(allocation)

    def sort_key(row: AllocationPerformance) -> tuple[int, Decimal, str]:
        if row.gain_loss is None:
            return (1, Decimal("0"), row.symbol)
        return (0, -row.gain_loss, row.symbol)

    return sorted(iterate_rows(), key=sort_key)


def version_return(version: FundVersion) -> VersionReturn:
    return VersionReturn(
        started_at=version.created_at,
        start_value=version.start_value,
        current_value=version.current_value,
        gain_loss=version.gain_loss,
        return_since_start=version.return_since_start,
    )


def allocation_changes(version: FundVersion) -> list[AllocationChange] | None:
    """
    Target-share differences between this fund version and its parent.

    A ticker missing from one side is treated as zero shares and zero target
    weight. Its return stays empty, because that side never measured one.
    """
    parent = version.parent
    if parent is None:
        return None

    previous = {
        allocation.ticker.symbol: allocation for allocation in parent.allocations.all()
    }
    current = {
        allocation.ticker.symbol: allocation for allocation in version.allocations.all()
    }

    def sort_key(symbol: str) -> tuple[int, str]:
        allocation = current.get(symbol)
        shares = 0 if allocation is None else allocation.shares
        return (-shares, symbol)

    def iterate_rows():
        for symbol in sorted(set(previous) | set(current), key=sort_key):
            yield _allocation_change(
                symbol,
                previous.get(symbol),
                current.get(symbol),
            )

    return list(iterate_rows())


def portfolio_contributions(version: PortfolioVersion) -> list[ContributionRow]:
    """
    Cash, each fund, and the portfolio total for one portfolio version.

    Contribution is that row's gain divided by the portfolio's starting budget
    (starting cash plus starting position value). Fund rows follow the same
    position totals the portfolio already sums, including a ticker that sits
    in more than one fund.
    """

    def contribution_of(gain: Decimal | None) -> Decimal | None:
        if gain is None or version.start_budget == 0:
            return None
        return gain / version.start_budget

    def iterate_rows():
        yield _cash_contribution(version, contribution_of)
        fund_versions = version.fund_versions.order_by("-start_value")
        for fund_version in fund_versions:
            yield ContributionRow(
                name=fund_version.fund.name,
                start_value=fund_version.start_value,
                current_value=fund_version.current_value,
                gain_loss=fund_version.gain_loss,
                return_since_start=fund_version.return_since_start,
                contribution=contribution_of(fund_version.gain_loss),
            )

        start_total = None
        if version.start_cash is not None or version.start_value is not None:
            start_total = version.start_budget
        yield ContributionRow(
            name="Total",
            start_value=start_total,
            current_value=version.current_budget,
            gain_loss=version.gain_loss,
            return_since_start=version.return_since_start,
            contribution=version.return_since_start,
        )

    return list(iterate_rows())


def portfolio_value_history(portfolio: Portfolio) -> list[PortfolioVersionReturn]:
    """
    Portfolio value at each version, oldest first.

    A closed version uses its stored end cash and end value. The active
    version uses live cash and live fund position values.
    """

    def iterate_versions():
        for version in portfolio.versions.order_by("created_at"):
            yield PortfolioVersionReturn(
                started_at=version.started_at or version.created_at,
                ended_at=version.ended_at,
                active=version.active,
                start_budget=version.start_budget,
                current_budget=version.current_budget,
                gain_loss=version.gain_loss,
                return_since_start=version.return_since_start,
            )

    return list(iterate_versions())


def _allocation_performance(allocation: FundVersionAllocation) -> AllocationPerformance:
    return AllocationPerformance(
        symbol=allocation.ticker.symbol,
        start_value=allocation.start_value,
        current_value=allocation.current_value,
        gain_loss=allocation.gain_loss,
        return_since_start=allocation.return_since_start,
        contribution=allocation.contribution,
        target_weight=allocation.target_weight,
        actual_weight=allocation.actual_weight,
        drift=allocation.drift,
    )


def _allocation_change(
    symbol: str,
    previous: FundVersionAllocation | None,
    current: FundVersionAllocation | None,
) -> AllocationChange:
    return AllocationChange(
        symbol=symbol,
        previous_shares=0 if previous is None else previous.shares,
        shares=0 if current is None else current.shares,
        previous_weight=Decimal("0") if previous is None else previous.target_weight,
        weight=Decimal("0") if current is None else current.target_weight,
        previous_return=None if previous is None else previous.return_since_start,
        return_since_start=None if current is None else current.return_since_start,
    )


def _cash_contribution(
    version: PortfolioVersion,
    contribution_of: Callable[[Decimal | None], Decimal | None],
) -> ContributionRow:
    if version.start_cash is None:
        cash_gain = None
        cash_return = None
    else:
        cash_gain = version.current_cash - version.start_cash
        if version.start_cash == 0:
            cash_return = None
        else:
            cash_return = cash_gain / version.start_cash

    return ContributionRow(
        name="Cash",
        start_value=version.start_cash,
        current_value=version.current_cash,
        gain_loss=cash_gain,
        return_since_start=cash_return,
        contribution=contribution_of(cash_gain),
    )

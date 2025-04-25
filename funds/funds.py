from collections.abc import Mapping
from decimal import Decimal

from django.db.models import prefetch_related_objects

from funds.models import FundVersion, FundVersionAllocation
from holdings.models import HoldingAccountPosition
from tickers.models import Ticker


def allocate_from_position(self: FundVersion) -> None:
    """
    Automatically allocate the fund allocations based on the percentage of
    assets are represented by the underlying positions.
    """
    tickers = Ticker.objects.filter(
        fund_allocations__version=self,
    )
    positions = HoldingAccountPosition.objects.filter(
        holding_account__owner=self.fund.owner,
        ticker__in=tickers,
    ).all()
    total_value = Decimal(
        sum(p.value or Decimal("0") for p in positions),
    )
    value_by_ticker: Mapping[str, Decimal] = {
        p.ticker.symbol: p.value for p in positions if p.ticker and p.value
    }
    if total_value == 0:
        return

    def iterate_allocations():
        for allocation in self.allocations.iterator():
            allocation.shares = int(
                value_by_ticker.get(allocation.ticker.symbol, Decimal("0"))
                / total_value
                * self.shares
            )
            yield allocation

    _ = FundVersionAllocation.objects.bulk_update(
        iterate_allocations(),
        fields=[
            "shares",
        ],
    )


def create_new_version(self: FundVersion) -> FundVersion:
    """
    Create a new :class:`FundVersion` from the given one.
    """
    fund_version = self.fund.versions.create(
        parent=self,
        portfolio_shares=self.portfolio_shares,
        portfolio_modifier=self.portfolio_modifier,
        confidence_shift_percentage=self.confidence_shift_percentage,
        shares=self.shares,
    )

    def iterate_allocations():
        for allocation in self.allocations.iterator():
            yield FundVersionAllocation(
                version=fund_version,
                ticker=allocation.ticker,
                weekly_confidence=allocation.weekly_confidence,
                monthly_confidence=allocation.monthly_confidence,
                quarterly_confidence=allocation.quarterly_confidence,
                modifier=allocation.modifier,
                shares=allocation.shares,
            )

    _ = FundVersionAllocation.objects.bulk_create(iterate_allocations())

    return fund_version


def apply_suggestions(self: FundVersion) -> None:
    """
    Apply suggested shares to this :class:`FundVersion`.
    """
    prefetch_related_objects(
        [self],
        *(FundVersion.Prefetch.PositionPercentage | FundVersion.Prefetch.PositionValue),
    )

    def iterate_allocations():
        for allocation in self.allocations.iterator():
            allocation.shares = allocation.suggested_shares
            yield allocation

    _ = FundVersionAllocation.objects.bulk_update(
        iterate_allocations(),
        fields=[
            "shares",
        ],
    )


def activate(self: FundVersion) -> None:
    """
    Activate this :class:`FundVersion`.
    """
    self.active = True
    self.save()

    _ = (
        FundVersion.objects.filter(
            fund=self.fund,
            active=True,
        )
        .exclude(pk=self.pk)
        .update(active=False)
    )

    self.fund.active_version = self  # pyright: ignore[reportAttributeAccessIssue]
    self.fund.save()

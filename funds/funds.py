from collections.abc import Mapping
from decimal import Decimal

from django.db.models import prefetch_related_objects

from funds.models import FundVersion, FundVersionAllocation
from funds.portfolio.models import PortfolioVersion
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


def create_new_version(
    self: FundVersion,
    portfolio_version: PortfolioVersion | None = None,
) -> FundVersion:
    """
    Create a new :class:`FundVersion` from the given one.
    """
    prefetch_related_objects([self], *FundVersion.Prefetch.PositionValue)

    # Update "end_value" for all of our allocations and ourselves.
    def iterate_old_allocations():
        for allocation in self.allocations.all():
            allocation.end_value = allocation.position_value
            yield allocation

    _ = FundVersionAllocation.objects.bulk_update(
        iterate_old_allocations(),
        fields=["end_value"],
    )
    self.end_value = Decimal(
        sum(
            allocation.end_value or Decimal("0")
            for allocation in self.allocations.all()
        )
    )
    self.save(update_fields=["end_value"])

    fund_version = self.fund.versions.create(
        parent=self,
        portfolio_shares=self.portfolio_shares,
        portfolio_modifier=self.portfolio_modifier,
        confidence_shift_percentage=self.confidence_shift_percentage,
        shares=self.shares,
        portfolio_version=portfolio_version,
    )

    def iterate_new_allocations():
        for allocation in self.allocations.all():
            yield FundVersionAllocation(
                version=fund_version,
                ticker=allocation.ticker,
                weekly_confidence=allocation.weekly_confidence,
                monthly_confidence=allocation.monthly_confidence,
                quarterly_confidence=allocation.quarterly_confidence,
                modifier=allocation.modifier,
                shares=allocation.shares,
                start_value=allocation.end_value,
            )

    _ = FundVersionAllocation.objects.bulk_create(iterate_new_allocations())
    fund_version.start_value = Decimal(
        sum(
            allocation.start_value or Decimal("0")
            for allocation in fund_version.allocations.all()
        )
    )
    fund_version.save(update_fields=["start_value"])

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


def reset_portfolio_to_value(self: FundVersion) -> None:
    """
    Reset portfolio shares to this fund's relative value
    """
    assert self.fund.portfolio is not None
    self.portfolio_shares = int(self.position_percentage * self.fund.portfolio.shares)
    self.save()

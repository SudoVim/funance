from collections.abc import Mapping
from decimal import Decimal

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

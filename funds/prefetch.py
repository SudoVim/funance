from django_helpers.prefetch import prefetch
from holdings.models import HoldingAccount


class FundVersionPrefetch:
    PositionValue = prefetch("allocations", "ticker") | prefetch(
        "fund",
        "portfolio",
        "holding_accounts",
        HoldingAccount.Prefetch.PositionsByTicker,
    )
    PositionPercentage = PositionValue | prefetch(
        "fund",
        "portfolio",
        "holding_accounts",
        HoldingAccount.Prefetch.PositionValue,
    )


class FundPrefetch:
    PositionValue = prefetch("active_version", FundVersionPrefetch.PositionValue)
    PositionPercentage = prefetch(
        "active_version", FundVersionPrefetch.PositionPercentage
    )


class FuncVersionAllocationPrefetch:
    PositionValue = prefetch("version", FundVersionPrefetch.PositionValue)
    PositionPercentage = prefetch("version", FundVersionPrefetch.PositionPercentage)

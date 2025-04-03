import uuid
from decimal import Decimal
from functools import cached_property
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet
from typing_extensions import override

from django_helpers.prefetch import prefetch
from holdings.models import HoldingAccount

if TYPE_CHECKING:
    from accounts.models import Account
    from tickers.models import Ticker


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


class Portfolio(models.Model):
    """
    The Portfolio model represents multiple funds in a portfolio
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    owner = models.ForeignKey["Account"](
        "accounts.Account", on_delete=models.CASCADE, related_name="portfolio"
    )

    name = models.CharField(max_length=64)

    funds: QuerySet["Fund"]  # pyright: ignore[reportUninitializedInstanceVariable]
    holding_accounts: QuerySet[HoldingAccount]  # pyright: ignore[reportUninitializedInstanceVariable]

    class Prefetch:
        AvailableCash = prefetch(
            "holding_accounts", HoldingAccount.Prefetch.AvailableCash
        )
        PositionValue = prefetch("funds", FundPrefetch.PositionValue)

    @cached_property
    def available_cash(self) -> Decimal:
        def iterate_cash():
            for holding_account in self.holding_accounts.all():
                yield holding_account.available_cash

        return Decimal(sum(iterate_cash()))

    @cached_property
    def cash_percent(self) -> Decimal:
        total_value = self.available_cash + self.position_value
        if total_value == 0:
            return Decimal("0")
        return self.available_cash / total_value

    @cached_property
    def position_value(self) -> Decimal:
        def iterate_position_value():
            for fund in self.funds.all():
                yield fund.position_value

        return Decimal(sum(iterate_position_value()))

    @override
    def __str__(self) -> str:
        return self.name


class Fund(models.Model):
    """
    The Fund model represents a single fund
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    owner = models.ForeignKey["Account"](
        "accounts.Account", on_delete=models.CASCADE, related_name="funds"
    )

    portfolio = models.ForeignKey["Portfolio"](
        "Portfolio",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="funds",
    )

    active_version = models.OneToOneField(
        "FundVersion",
        on_delete=models.SET_NULL,
        related_name="+",
        blank=True,
        null=True,
    )

    versions: QuerySet["FundVersion"]  # pyright: ignore[reportUninitializedInstanceVariable]

    #: Name of the fund
    name = models.CharField(max_length=64)

    Prefetch = FundPrefetch

    @cached_property
    def position_value(self) -> Decimal:
        if self.active_version is None:
            return Decimal("0")
        return self.active_version.position_value

    @cached_property
    def position_percentage(self) -> Decimal:
        if self.active_version is None:
            return Decimal("0")
        return self.active_version.position_percentage

    @override
    def __str__(self) -> str:
        return self.name


class FundVersion(models.Model):
    """
    The FundVersion model represents a version of a single fund
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    fund = models.ForeignKey["Fund"](
        "Fund", on_delete=models.CASCADE, related_name="versions"
    )

    parent = models.ForeignKey["FundVersion"](
        "FundVersion",
        on_delete=models.CASCADE,
        related_name="children",
        blank=True,
        null=True,
    )

    active = models.BooleanField(default=False)

    #: Total number of shares available to allocate
    shares = models.PositiveIntegerField(default=1000)

    allocations: QuerySet["FundVersionAllocation"]  # pyright: ignore[reportUninitializedInstanceVariable]

    Prefetch = FundVersionPrefetch

    class Meta:
        indexes = [
            models.Index(fields=["active"]),
        ]

    @cached_property
    def ticker_set(self) -> set[str]:
        def iterate_tickers():
            for allocation in self.allocations.all():
                yield allocation.ticker.symbol

        return set(iterate_tickers())

    @cached_property
    def position_value(self) -> Decimal:
        def iterate_positions():
            if self.fund.portfolio is None:
                return
            for holding_account in self.fund.portfolio.holding_accounts.all():
                for (
                    ticker_symbol,
                    position,
                ) in holding_account.positions_by_ticker.items():
                    if ticker_symbol not in self.ticker_set:
                        continue
                    if position.value is None:
                        continue
                    yield position.value

        return Decimal(sum(iterate_positions()))

    @cached_property
    def position_percentage(self) -> Decimal:
        if self.fund.portfolio is None:
            return Decimal("0")
        portfolio_value = self.fund.portfolio.position_value
        if portfolio_value == 0:
            return Decimal("0")
        return self.position_value / portfolio_value

    @override
    def __str__(self) -> str:
        return " - ".join(
            [
                self.fund.name,
                self.created_at.strftime("%c"),
            ]
        )


class FundVersionAllocation(models.Model):
    """
    The FundVersionAllocation model represents an allocation in a version of a
    fund
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    version = models.ForeignKey["FundVersion"](
        "FundVersion",
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    ticker = models.ForeignKey["Ticker"](
        "tickers.Ticker",
        on_delete=models.CASCADE,
        related_name="fund_allocations",
    )

    #: Total number of shares allocated to this ticker
    shares = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = (
            "version",
            "ticker",
        )

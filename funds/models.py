import uuid
from decimal import Decimal
from functools import cached_property
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet
from typing_extensions import override

from funds.confidence import Confidence, ConfidenceList
from funds.portfolio.models import *
from funds.prefetch import (
    FuncVersionAllocationPrefetch,
    FundPrefetch,
    FundVersionPrefetch,
)

if TYPE_CHECKING:
    from accounts.models import Account
    from tickers.models import Ticker


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

    @property
    def position_value(self) -> Decimal:
        if self.active_version is None:
            return Decimal("0")
        return self.active_version.position_value

    @property
    def position_percentage(self) -> Decimal:
        if self.active_version is None:
            return Decimal("0")
        return self.active_version.position_percentage

    @property
    def portfolio_shares(self) -> int:
        if self.active_version is None:
            return 0
        return self.active_version.portfolio_shares

    @property
    def portfolio_percentage(self) -> Decimal:
        if self.active_version is None:
            return Decimal("0")
        return self.active_version.portfolio_percentage

    @property
    def budget(self) -> Decimal:
        if self.active_version is None:
            return Decimal("0")
        return self.active_version.budget

    @property
    def budget_delta(self) -> Decimal:
        return self.budget - self.position_value

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

    portfolio_shares = models.PositiveIntegerField(default=1000)

    portfolio_modifier = models.IntegerField(default=100)

    #: Total number of shares available to allocate
    shares = models.PositiveIntegerField(default=1000)

    confidence_shift_percentage = models.PositiveIntegerField(default=20)

    allocations: QuerySet["FundVersionAllocation"]  # pyright: ignore[reportUninitializedInstanceVariable]
    children: QuerySet["FundVersion"]  # pyright: ignore[reportUninitializedInstanceVariable]

    Prefetch = FundVersionPrefetch

    class Meta:
        indexes = [
            models.Index(fields=["active"]),
        ]

    @property
    def portfolio_percentage(self) -> Decimal:
        if self.fund.portfolio is None:
            return Decimal("0")
        if self.fund.portfolio.shares == 0:
            return Decimal("0")
        return Decimal(self.portfolio_shares) / self.fund.portfolio.shares

    @property
    def budget(self) -> Decimal:
        if self.fund.portfolio is None:
            return Decimal("0")
        return self.portfolio_percentage * self.fund.portfolio.total_value

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

    @property
    def position_percentage(self) -> Decimal:
        if self.fund.portfolio is None:
            return Decimal("0")
        portfolio_value = self.fund.portfolio.total_value
        if portfolio_value == 0:
            return Decimal("0")
        return self.position_value / portfolio_value

    @cached_property
    def confidence(self) -> ConfidenceList:
        def iterate_confidence():
            for allocation in self.allocations.all():
                for confidence in allocation.confidence:
                    yield confidence

        return ConfidenceList(iterate_confidence())

    @cached_property
    def confidence_shares(self) -> Decimal:
        return self.confidence.confidence_shares

    @cached_property
    def confidence_percentage(self) -> Decimal:
        return self.confidence.confidence

    @cached_property
    def unmodified_suggested_shares(self) -> int:
        return sum(a.unmodified_suggested_shares for a in self.allocations.all())

    @property
    def portfolio_confidence_percentage(self) -> Decimal:
        if self.fund.portfolio is None or self.fund.portfolio.total_confidence == 0:
            return Decimal("0")
        return self.confidence_percentage / self.fund.portfolio.total_confidence

    @property
    def unmodified_portfolio_shares(self) -> int:
        if self.fund.portfolio is None:
            return 0
        total_shares = int(
            self.portfolio_confidence_percentage * self.fund.portfolio.shares
        )
        confidence_change = (total_shares - self.portfolio_shares) * (
            Decimal(self.fund.portfolio.confidence_shift_percentage) / 100
        )
        return (
            max(
                int(Decimal(self.portfolio_modifier) / 100 * confidence_change),
                -self.portfolio_shares,
            )
            + self.portfolio_shares
        )

    @property
    def suggested_portfolio_shares(self) -> int:
        if (
            self.fund.portfolio is None
            or self.fund.portfolio.unmodified_portfolio_shares == 0
        ):
            return 0
        return int(
            self.unmodified_portfolio_shares
            / self.fund.portfolio.unmodified_portfolio_shares
            * self.fund.portfolio.shares
        )

    @property
    def suggested_portfolio_change_percent(self) -> Decimal:
        return (
            Decimal(self.suggested_portfolio_shares - self.portfolio_shares)
            / self.portfolio_shares
        )

    @property
    def suggested_portfolio_change_value(self) -> Decimal:
        return self.suggested_portfolio_change_percent * self.position_value

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

    weekly_confidence = models.PositiveIntegerField(default=0)
    monthly_confidence = models.PositiveIntegerField(default=0)
    quarterly_confidence = models.PositiveIntegerField(default=0)

    modifier = models.IntegerField(default=100)

    #: Total number of shares allocated to this ticker
    shares = models.PositiveIntegerField(default=0)

    Prefetch = FuncVersionAllocationPrefetch

    class Meta:
        unique_together = (
            "version",
            "ticker",
        )

    @cached_property
    def position_value(self) -> Decimal:
        def iterate_accounts():
            if self.version.fund.portfolio is None:
                return
            for holding_account in self.version.fund.portfolio.holding_accounts.all():
                position = holding_account.positions_by_ticker.get(self.ticker.symbol)
                if not position or not position.value:
                    continue
                yield position.value

        return Decimal(sum(iterate_accounts()))

    @property
    def position_percentage(self) -> Decimal:
        return self.position_value / self.version.position_value

    @property
    def budget_percentage(self) -> Decimal:
        if self.version.shares == 0:
            return Decimal("0")
        return Decimal(self.shares) / self.version.shares

    @property
    def budget(self) -> Decimal:
        return self.version.budget * self.budget_percentage

    @property
    def budget_delta(self) -> Decimal:
        return self.budget - self.position_value

    @property
    def budget_delta_shares(self) -> Decimal:
        if self.ticker.current_price == 0:
            return Decimal("0")
        return (self.budget_delta / self.ticker.current_price).quantize(Decimal("0.01"))

    @cached_property
    def confidence(self) -> ConfidenceList:
        return ConfidenceList(
            [
                Confidence.weekly(self.weekly_confidence, self.position_percentage),
                Confidence.monthly(self.monthly_confidence, self.position_percentage),
                Confidence.quarterly(
                    self.quarterly_confidence, self.position_percentage
                ),
            ],
        )

    @cached_property
    def confidence_shares(self) -> Decimal:
        return self.confidence.confidence_shares

    @property
    def confidence_percentage(self) -> Decimal:
        if self.version.confidence_shares == 0:
            return Decimal("0")
        return self.confidence_shares / self.version.confidence_shares

    @property
    def unmodified_suggested_shares(self) -> int:
        """
        The new amount of shares recommended based on the confidence
        percentage, the shift percentage of the version, and the modifier.
        """
        total_shares = int(self.confidence_percentage * self.version.shares)
        confidence_change = (total_shares - self.shares) * (
            Decimal(self.version.confidence_shift_percentage) / 100
        )
        return (
            max(
                int(Decimal(self.modifier) / 100 * confidence_change),
                -self.shares,
            )
            + self.shares
        )

    @property
    def suggested_shares(self) -> int:
        return int(
            self.unmodified_suggested_shares
            / self.version.unmodified_suggested_shares
            * self.version.shares
        )

    @property
    def suggested_change_percent(self) -> Decimal:
        if self.shares == 0:
            return Decimal("0")
        return Decimal(self.suggested_shares - self.shares) / self.shares

    @property
    def suggested_change(self) -> Decimal:
        return self.suggested_change_percent * self.budget

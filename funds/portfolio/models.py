import datetime
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet
from django.utils.functional import cached_property
from typing_extensions import override

from django_helpers.prefetch import prefetch
from funds.prefetch import FundPrefetch
from holdings.models import HoldingAccount

if TYPE_CHECKING:
    from accounts.models import Account
    from funds.models import Fund
    from funds.portfolio.performance import Performance


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

    shares = models.PositiveIntegerField(default=10000)

    funds: QuerySet["Fund"]  # pyright: ignore[reportUninitializedInstanceVariable]
    holding_accounts: QuerySet[HoldingAccount]  # pyright: ignore[reportUninitializedInstanceVariable]
    weeks: QuerySet["PortfolioWeek"]  # pyright: ignore[reportUninitializedInstanceVariable]

    class Prefetch:
        AvailableCash = prefetch(
            "holding_accounts", HoldingAccount.Prefetch.AvailableCash
        )
        PositionValue = prefetch("funds", FundPrefetch.PositionValue)

    @cached_property
    def position_shares(self) -> int:
        return sum(f.portfolio_shares for f in self.funds.all())

    @property
    def cash_shares(self) -> int:
        return self.shares - self.position_shares

    @property
    def total_value(self) -> Decimal:
        return self.available_cash + self.position_value

    @cached_property
    def available_cash(self) -> Decimal:
        def iterate_cash():
            for holding_account in self.holding_accounts.all():
                yield holding_account.available_cash

        return Decimal(sum(iterate_cash()))

    @property
    def cash_percent(self) -> Decimal:
        if self.total_value == 0:
            return Decimal("0")
        return self.available_cash / self.total_value

    @cached_property
    def position_value(self) -> Decimal:
        def iterate_position_value():
            for fund in self.funds.all():
                yield fund.position_value

        return Decimal(sum(iterate_position_value()))

    @override
    def __str__(self) -> str:
        return self.name


class PortfolioWeek(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    portfolio = models.ForeignKey["Portfolio"](
        "Portfolio",
        on_delete=models.CASCADE,
        related_name="weeks",
    )

    date = models.DateField()

    sale_profit = models.DecimalField(
        max_digits=32, decimal_places=8, blank=True, null=True
    )
    sale_interest = models.DecimalField(
        max_digits=32, decimal_places=8, blank=True, null=True
    )
    generation_profit = models.DecimalField(
        max_digits=32, decimal_places=8, blank=True, null=True
    )
    net_cost_basis = models.DecimalField(
        max_digits=32, decimal_places=8, blank=True, null=True
    )

    @cached_property
    def performance(self) -> "Performance":
        from funds.portfolio.performance import Performance, PerformanceQuery

        return Performance(
            PerformanceQuery(
                self.portfolio,
                self.date,
                self.date + datetime.timedelta(days=7),
            ),
        )

    @property
    def total_profit(self) -> Decimal | None:
        if self.sale_profit is None or self.generation_profit is None:
            return None
        return self.sale_profit + self.generation_profit

    class Meta:
        unique_together = (
            "portfolio",
            "date",
        )

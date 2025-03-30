import uuid
from typing import TYPE_CHECKING

from django.db import models
from django.db.models import QuerySet
from typing_extensions import override

if TYPE_CHECKING:
    from accounts.models import Account
    from tickers.models import Ticker


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

    class Meta:
        indexes = [
            models.Index(fields=["active"]),
        ]

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

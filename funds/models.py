import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class Fund(models.Model):
    """
    The Fund model represents a single fund, which consists of an array of
    purchases of different tickers.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        "accounts.Account", on_delete=models.CASCADE, related_name="funds"
    )

    #: Name of the fund
    name = models.CharField(max_length=64)

    #: Total number of shares available to allocate
    shares = models.IntegerField(default=1000)


class FundAllocation(models.Model):
    """
    The FundAllocation model represents an allocation in a fund of a single
    ticker. This is used for planning
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    fund = models.ForeignKey(
        "Fund",
        on_delete=models.CASCADE,
        related_name="allocations",
    )
    ticker = models.ForeignKey(
        "tickers.Ticker",
        on_delete=models.CASCADE,
        related_name="fund_allocations",
    )

    #: Name of the allocation
    name = models.CharField(max_length=64)

    #: Total number of shares allocated to this ticker
    shares = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

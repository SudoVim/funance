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

    class Currency(models.TextChoices):
        USD = ("US", _("USD"))

    #: The currency represented by this fund
    currency = models.CharField(
        max_length=2, choices=Currency.choices, default=Currency.USD
    )

    #: The amount of cash that's available for purchase
    available_cash = models.DecimalField(max_digits=32, decimal_places=4)


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

    #: The percentage of the fund allocation desired by this security
    percentage = models.DecimalField(max_digits=7, decimal_places=4)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class FundPurchase(models.Model):
    """
    The FundPurchase model represents a single func purchase, which is a
    point-in-time purchase of a ticker at a price.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    fund = models.ForeignKey(
        "Fund",
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    ticker = models.ForeignKey(
        "tickers.Ticker",
        on_delete=models.CASCADE,
        related_name="fund_purchases",
    )

    #: The quantity of the security to buy. I gave this four decimal places in
    #  case the security can be bought in fractions.
    quantity = models.DecimalField(max_digits=32, decimal_places=4)

    #: The price of the security at purchase time.
    price = models.DecimalField(max_digits=32, decimal_places=4)

    created_at = models.DateTimeField(auto_now_add=True)
    purchased_at = models.DateTimeField()

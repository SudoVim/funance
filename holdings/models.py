import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class HoldingAccount(models.Model):
    """
    The HoldingAccount model represents an account that can hold assets, which
    consists of an array of purchases of different tickers and a cash reserve.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey(
        "accounts.Account", on_delete=models.CASCADE, related_name="holding_accounts"
    )

    #: Name of the account
    name = models.CharField(max_length=64)

    class Currency(models.TextChoices):
        USD = ("US", _("USD"))

    #: The currency represented by this account
    currency = models.CharField(
        max_length=2, choices=Currency.choices, default=Currency.USD
    )

    @property
    def currency_label(self):
        return self.Currency(self.currency).label

    #: The amount of cash that's available for purchase
    available_cash = models.DecimalField(max_digits=32, decimal_places=4, default=0)

    @property
    def available_cash_value(self):
        return int(self.available_cash)


class HoldingAccountPurchase(models.Model):
    """
    The HoldingPurchase model represents a single purchase on a holding
    account, which is a point-in-time purchase of a ticker at a price.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    holding_account = models.ForeignKey(
        "HoldingAccount",
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    ticker = models.ForeignKey(
        "tickers.Ticker",
        on_delete=models.CASCADE,
        related_name="holding_account_purchases",
    )

    #: The quantity of the security to buy. I gave this eight decimal places in
    #  case the security can be bought in fractions. Bitcoin, for instance, can
    #  be bought in hundred millionths.
    quantity = models.DecimalField(max_digits=32, decimal_places=8)

    @property
    def quantity_value(self):
        return float(self.quantity)

    #: The price of the security at purchase time.
    price = models.DecimalField(max_digits=32, decimal_places=4)

    @property
    def price_value(self):
        return float(self.price)

    created_at = models.DateTimeField(auto_now_add=True)
    purchased_at = models.DateTimeField()

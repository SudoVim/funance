import uuid
from decimal import Decimal
from typing import Literal

from django.db import models
from django.utils.translation import gettext_lazy as _
from typing_extensions import override

from accounts.models import Account
from tickers.models import Ticker


class HoldingAccount(models.Model):
    """
    The HoldingAccount model represents an account that can hold assets, which
    consists of an array of purchases of different tickers and a cash reserve.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey[Account](
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
    available_cash = models.DecimalField(
        max_digits=32, decimal_places=4, default=Decimal("0")
    )

    @property
    def available_cash_value(self) -> Decimal:
        return self.available_cash

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @override
    def __str__(self) -> str:
        return "  ".join(
            [
                self.owner.first_name,
                self.owner.last_name,
                self.name,
            ]
        )


class HoldingAccountPurchase(models.Model):
    """
    The HoldingPurchase model represents a single purchase on a holding
    account, which is a point-in-time purchase of a ticker at a price.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    holding_account = models.ForeignKey["HoldingAccount"](
        "HoldingAccount",
        on_delete=models.CASCADE,
        related_name="purchases",
    )

    @property
    def account_name(self) -> str:
        """
        Name of the associated account.
        """
        return self.holding_account.name

    ticker = models.ForeignKey[Ticker](
        "tickers.Ticker",
        on_delete=models.CASCADE,
        related_name="holding_account_purchases",
    )

    @property
    def ticker_symbol(self) -> str:
        """
        Ticker symbol represented by this purchase.
        """
        return self.ticker.symbol

    Operation = Literal["BUY", "SELL"]

    @property
    def operation(self) -> Operation:
        """
        Operation performed.
        """
        if self.quantity >= 0:
            return "BUY"

        return "SELL"

    #: The quantity of the security to buy. I gave this eight decimal places in
    #  case the security can be bought in fractions. Bitcoin, for instance, can
    #  be bought in hundred millionths.
    quantity = models.DecimalField(max_digits=32, decimal_places=8)

    @property
    def quantity_value(self):
        return float(self.quantity)

    @property
    def abs_quantity_value(self):
        return abs(self.quantity_value)

    #: The price of the security at purchase time.
    price = models.DecimalField(max_digits=32, decimal_places=8)

    @property
    def price_value(self):
        return float(self.price)

    created_at = models.DateTimeField(auto_now_add=True)
    purchased_at = models.DateTimeField()

    @override
    def __str__(self) -> str:
        return str(self.id)


def holding_account_document_upload_to(
    document: "HoldingAccountDocument", filename: str
) -> str:
    return "/".join(
        [
            "data",
            "holding_account_documents",
            document.created_at.strftime("%Y"),
            document.created_at.strftime("%m"),
            document.created_at.strftime("%d"),
            str(document.holding_account.id),
            "-".join(
                [
                    str(document.id).split("-")[0],
                    filename,
                ]
            ),
        ]
    )


class HoldingAccountDocument(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    holding_account = models.ForeignKey[HoldingAccount](
        "HoldingAccount",
        on_delete=models.CASCADE,
        related_name="documents",
    )

    document = models.FileField(
        max_length=256, upload_to=holding_account_document_upload_to
    )

    class DocumentType(models.TextChoices):
        pass

    @override
    def __str__(self) -> str:
        return self.document.name.split("/")[-1]

import uuid
from decimal import Decimal

from django.db import models
from django.utils.translation import gettext_lazy as _
from typing_extensions import override

from accounts.models import Account
from holdings.positions import PositionAction, PositionSale


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

    #: The unique account number
    number = models.CharField(max_length=32)

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

    aliases: models.QuerySet["HoldingAccountAlias"]  # pyright: ignore[reportUninitializedInstanceVariable]
    documents: models.QuerySet["HoldingAccountDocument"]  # pyright: ignore[reportUninitializedInstanceVariable]
    positions: models.QuerySet["HoldingAccountPosition"]  # pyright: ignore[reportUninitializedInstanceVariable]

    @property
    def aliases_dict(self) -> dict[str, str]:
        """
        The symbol aliases associated with this account.
        """
        return {a.discoverable: a.alias for a in self.aliases.all()}

    @override
    def __str__(self) -> str:
        return "  ".join(
            [
                self.owner.first_name,
                self.owner.last_name,
                self.name,
            ]
        )


class HoldingAccountAlias(models.Model):
    """
    An alias representing a mapping of a discoverable symbol to a symbol that
    we recognize.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    holding_account = models.ForeignKey["HoldingAccount"](
        "HoldingAccount",
        on_delete=models.CASCADE,
        related_name="aliases",
    )

    discoverable = models.CharField(max_length=16)
    alias = models.CharField(max_length=16)


class HoldingAccountPosition(models.Model):
    """
    Model representing a position of a :class:`HoldingAccount`.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    holding_account = models.ForeignKey["HoldingAccount"](
        "HoldingAccount",
        on_delete=models.CASCADE,
        related_name="positions",
    )

    ticker_symbol = models.CharField(max_length=16)

    actions: models.QuerySet["HoldingAccountAction"]  # pyright: ignore[reportUninitializedInstanceVariable]
    sales: models.QuerySet["HoldingAccountSale"]  # pyright: ignore[reportUninitializedInstanceVariable]
    generations: models.QuerySet["HoldingAccountGeneration"]  # pyright: ignore[reportUninitializedInstanceVariable]

    class Meta:
        unique_together = "holding_account", "ticker_symbol"


class HoldingAccountAction(models.Model):
    """
    The HoldingAccountAction model represents a single action taken on a
    position - generally "buy" or "sell".
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    position = models.ForeignKey["HoldingAccountPosition"](
        "HoldingAccountPosition",
        on_delete=models.CASCADE,
        related_name="actions",
    )

    purchased_on = models.DateField()

    class Action(models.TextChoices):
        BUY = "buy"
        SELL = "sell"

    action = models.CharField(max_length=16, choices=Action.choices)

    #: The quantity of the security to buy. I gave this eight decimal places in
    #  case the security can be bought in fractions. Bitcoin, for instance, can
    #  be bought in hundred millionths.
    quantity = models.DecimalField(max_digits=32, decimal_places=8)

    #: The price of the security at purchase time.
    price = models.DecimalField(max_digits=32, decimal_places=8)

    @property
    def position_action(self) -> PositionAction:
        """
        Action object representing this database entry.
        """
        return PositionAction(
            self.position.ticker_symbol,
            self.purchased_on,
            self.action,  # pyright: ignore[reportArgumentType]
            self.quantity,
            self.price,
        )

    class Meta:
        indexes = [
            models.Index(fields=["purchased_on"]),
        ]


class HoldingAccountSale(models.Model):
    """
    The HoldingAccountSale model represents a single sale taken on a position
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    position = models.ForeignKey["HoldingAccountPosition"](
        "HoldingAccountPosition",
        on_delete=models.CASCADE,
        related_name="sales",
    )

    quantity = models.DecimalField(max_digits=32, decimal_places=8)

    purchase_date = models.DateField()

    purchase_price = models.DecimalField(max_digits=32, decimal_places=8)

    sale_date = models.DateField()

    sale_price = models.DecimalField(max_digits=32, decimal_places=8)

    @override
    def __str__(self) -> str:
        return str(self.id)

    @property
    def position_sale(self) -> PositionSale:
        """
        :class:`PositionSale` object representing this database entry.
        """
        return PositionSale(
            self.position.ticker_symbol,
            self.quantity,
            self.purchase_date,
            self.purchase_price,
            self.sale_date,
            self.sale_price,
        )

    @property
    def profit(self) -> Decimal:
        return self.position_sale.profit()

    class Meta:
        indexes = [
            models.Index(fields=["purchase_date"]),
            models.Index(fields=["sale_date"]),
        ]


class HoldingAccountGeneration(models.Model):
    """
    The HoldingAccountGeneration model represents a single capital generation
    for a position - generally dividends or interest events"
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    position = models.ForeignKey["HoldingAccountPosition"](
        "HoldingAccountPosition",
        on_delete=models.CASCADE,
        related_name="generations",
    )

    date = models.DateField()

    class Event(models.TextChoices):
        DIVIDEND = "dividend"
        LONG_TERM_CAP_GAIN = "long-term-cap-gain"
        SHORT_TERM_CAP_GAIN = "short-term-cap-gain"
        INTEREST = "interest"
        ROYALTY_PAYMENT = "royalty-payment"
        RETURN_OF_CAPITAL = "return-of-capital"
        FOREIGN_TAX = "foreign-tax"
        FEE = "fee"

    event = models.CharField(max_length=32, choices=Event.choices)

    amount = models.DecimalField(max_digits=32, decimal_places=8)

    cost_basis = models.DecimalField(max_digits=32, decimal_places=8)

    @override
    def __str__(self) -> str:
        return str(self.id)

    class Meta:
        indexes = [
            models.Index(fields=["date"]),
        ]


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
        STATEMENT = "statement"
        ACTIVITY = "activity"

    document_type = models.CharField(
        max_length=16,
        choices=DocumentType.choices,
        default=DocumentType.ACTIVITY,
    )

    order = models.PositiveIntegerField(blank=True, null=True)

    @override
    def __str__(self) -> str:
        return self.document.name.split("/")[-1]

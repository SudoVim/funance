import datetime
import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from django.db import models
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
from typing_extensions import override

from holdings.positions.action import PositionAction
from holdings.positions.action_list import ActionList
from holdings.positions.available_purchases import AvailablePurchases
from holdings.positions.generation import PositionGeneration
from holdings.positions.generation_list import GenerationList
from holdings.positions.position import Position
from holdings.positions.sale import PositionSale
from holdings.positions.sale_list import SaleList

if TYPE_CHECKING:
    from accounts.models import Account
    from funds.models import Portfolio


class HoldingAccount(models.Model):
    """
    The HoldingAccount model represents an account that can hold assets, which
    consists of an array of purchases of different tickers and a cash reserve.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    owner = models.ForeignKey["Account"](
        "accounts.Account", on_delete=models.CASCADE, related_name="holding_accounts"
    )

    portfolio = models.ForeignKey["Portfolio"](
        "funds.Portfolio",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="holding_accounts",
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
    ticker = models.ForeignKey(
        "tickers.Ticker",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="holding_account_positions",
    )

    quantity = models.DecimalField(
        max_digits=32, decimal_places=8, blank=True, null=True
    )
    cost_basis = models.DecimalField(
        max_digits=32, decimal_places=8, blank=True, null=True
    )

    actions: models.QuerySet["HoldingAccountAction"]  # pyright: ignore[reportUninitializedInstanceVariable]
    sales: models.QuerySet["HoldingAccountSale"]  # pyright: ignore[reportUninitializedInstanceVariable]
    generations: models.QuerySet["HoldingAccountGeneration"]  # pyright: ignore[reportUninitializedInstanceVariable]

    class Meta:
        ordering = ["ticker_symbol"]
        unique_together = "holding_account", "ticker_symbol"
        indexes = [
            models.Index(fields=["quantity"]),
        ]

    @cached_property
    def position(self) -> Position:
        """
        :class:`Position` representing this position.
        """
        return Position(
            self.ticker_symbol,
            self.action_list,
            self.generation_list,
            self.quantity,
            self.cost_basis,
            self.available_purchases,
            self.sale_list,
        )

    @cached_property
    def action_list(self) -> ActionList:
        """
        :class:`ActionList` representing all actions
        """
        return ActionList(a.position_action for a in self.actions.all())

    @cached_property
    def sale_list(self) -> SaleList:
        """
        :class:`SaleList` representing all sales
        """
        return SaleList(s.position_sale for s in self.sales.all())

    @cached_property
    def available_purchases(self) -> AvailablePurchases:
        """
        :class:`SaleList` representing all sales
        """

        def iterate_available_purchases():
            for action in self.actions.all():
                available_purchase = action.available_purchase
                if available_purchase is None:
                    continue
                yield available_purchase

        return AvailablePurchases(iterate_available_purchases())

    @cached_property
    def total_sale_profit(self) -> Decimal:
        return self.sale_list.total_profit()

    @cached_property
    def total_sale_interest(self) -> Decimal:
        return self.sale_list.total_interest()

    @cached_property
    def generation_list(self) -> GenerationList:
        """
        :class:`GenerationList` representing all generations
        """
        return GenerationList(g.position_generation for g in self.generations.all())

    @cached_property
    def total_generation_profit(self) -> Decimal:
        return self.generation_list.total_profit()

    @cached_property
    def first_purchase(self) -> datetime.date | None:
        if self.actions.count() == 0:
            return None
        return min(a.purchased_on for a in self.actions.all())

    @cached_property
    def generation_frequency(self) -> Decimal:
        first_purchase = self.first_purchase
        if first_purchase is None:
            return Decimal("0")
        today = datetime.date.today()
        return self.generation_list.frequency((today - first_purchase).days)

    @cached_property
    def average_generation_interest(self) -> Decimal:
        first_purchase = self.first_purchase
        if first_purchase is None:
            return Decimal("0")
        today = datetime.date.today()
        return self.generation_list.average_interest((today - first_purchase).days)

    @cached_property
    def total_profit(self) -> Decimal:
        return self.total_sale_profit + self.total_generation_profit

    @cached_property
    def total_interest(self) -> Decimal:
        return self.total_sale_interest + self.average_generation_interest

    @cached_property
    def value(self) -> Decimal | None:
        if not self.ticker or not self.ticker.price:
            return None
        return self.available_purchases.potential_value(self.ticker.price)


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
    #: case the security can be bought in fractions. Bitcoin, for instance, can
    #: be bought in hundred millionths.
    quantity = models.DecimalField(max_digits=32, decimal_places=8)

    #: The remaining quantity for "buy" actions that haven't yet been used for
    #: "sell" actions.
    remaining_quantity = models.DecimalField(
        max_digits=32, decimal_places=8, blank=True, null=True
    )

    has_remaining_quantity = models.BooleanField(default=True)

    #: The price of the security at purchase time.
    price = models.DecimalField(max_digits=32, decimal_places=8)

    @cached_property
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

    @cached_property
    def available_purchase(self) -> PositionAction | None:
        """
        Action object representing this action as an available purchase if it
        can be.
        """
        if self.action != self.Action.BUY:
            return None
        if self.remaining_quantity is None or self.remaining_quantity <= 0:
            return None
        return PositionAction(
            self.position.ticker_symbol,
            self.purchased_on,
            self.action,  # pyright: ignore[reportArgumentType]
            self.remaining_quantity,
            self.price,
        )

    class Meta:
        ordering = ["purchased_on"]
        indexes = [
            models.Index(fields=["purchased_on"]),
            models.Index(fields=["action"]),
            models.Index(fields=["has_remaining_quantity"]),
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
        ordering = ["sale_date"]
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

    @property
    def position_generation(self) -> PositionGeneration:
        return PositionGeneration(
            self.position.ticker_symbol,
            self.date,
            self.event,  # pyright: ignore[reportArgumentType]
            self.amount,
            self.cost_basis,
        )

    class Meta:
        ordering = ["date"]
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

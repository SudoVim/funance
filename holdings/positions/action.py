import datetime
from decimal import Decimal
from typing import Literal, TypedDict

from typing_extensions import override

from holdings.positions.common import Copyable, Pythonable
from holdings.positions.unique import Unique

Action = Literal["buy", "sell"]


class PositionActionDict(TypedDict):
    symbol: str
    date: datetime.date
    action: Action
    quantity: Decimal
    price: Decimal
    total: Decimal


PositionActionKey = tuple[datetime.date, Action, Decimal, Decimal]


class PositionAction(
    Pythonable["PositionActionDict"],
    Copyable,
    Unique,
):
    """
    A single action for a position held in an account.

    .. automethod:: add_split
    .. automethod:: potential_profit
    .. automethod:: potential_interest
    .. automethod:: total_profit
    .. automethod:: average_potential_interest
    """

    Pythonic = PositionActionDict
    Key = PositionActionKey

    symbol: str
    date: datetime.date
    action: Action
    quantity: Decimal
    price: Decimal

    def __init__(
        self,
        symbol: str,
        date: datetime.date,
        action: Action,
        quantity: Decimal,
        price: Decimal,
    ) -> None:
        self.symbol = symbol
        self.date = date
        self.action = action
        self.quantity = quantity
        self.price = price

    def add_split(self, new_symbol: str, proportion: Decimal) -> "PositionAction":
        """
        Recalculate this action after a split.
        """
        return PositionAction(
            new_symbol,
            self.date,
            self.action,
            quantity=self.quantity * proportion,
            price=self.price / proportion,
        )

    def potential_profit(self, price: Decimal) -> Decimal:
        """
        Calculate the potential profit from this sale.
        """
        return (price - self.price) * self.quantity

    def potential_interest(self, today: datetime.date, price: Decimal) -> Decimal:
        """
        Calculate the converted interest of the sale.
        """
        days = Decimal((today - self.date).days)
        year_percent = Decimal("1") if not days else days / Decimal("365.25")
        return self.potential_profit(price) / self.quantity / self.price / year_percent

    @classmethod
    def total_profit(
        cls, price: Decimal, available_purchases: list["PositionAction"]
    ) -> Decimal:
        """
        Determine the total profit of the outstanding position denoted by
        *available_purchases*.
        """
        return Decimal(sum(a.potential_profit(price) for a in available_purchases))

    @classmethod
    def average_potential_interest(
        cls,
        today: datetime.date,
        price: Decimal,
        available_purchases: list["PositionAction"],
    ) -> Decimal:
        """
        Determine the average potential interest of the outstanding position
        denoted by *available_purchases*.
        """
        return Decimal(
            sum(
                a.potential_interest(today, price) * a.quantity
                for a in available_purchases
            )
        ) / sum(a.quantity for a in available_purchases)

    @override
    def to_python(self) -> Pythonic:
        return {
            "symbol": self.symbol,
            "date": self.date,
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "total": self.quantity * self.price,
        }

    @classmethod
    @override
    def from_python(cls, raw: Pythonic) -> "PositionAction":
        return cls(
            raw["symbol"],
            raw["date"],
            raw["action"],
            raw["quantity"],
            raw["price"],
        )

    @override
    def copy(self) -> "PositionAction":
        return PositionAction(
            symbol=self.symbol,
            date=self.date,
            action=self.action,
            quantity=self.quantity,
            price=self.price,
        )

    @override
    def key(self) -> "PositionAction.Key":
        return self.date, self.action, self.quantity, self.price

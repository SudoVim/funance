import datetime
from decimal import Decimal
from typing import TypedDict

from typing_extensions import override

from holdings.positions.common import Copyable, Pythonable


class PositionSaleDict(TypedDict):
    symbol: str
    quantity: Decimal
    purchase_date: datetime.date
    purchase_price: Decimal
    sale_date: datetime.date
    sale_price: Decimal
    profit: Decimal
    interest: Decimal


class PositionSale(Pythonable["PositionSaleDict"], Copyable):
    """
    Object representing the sale of a position.

    .. automethod:: profit
    .. automethod:: interest
    """

    symbol: str
    quantity: Decimal
    purchase_date: datetime.date
    purchase_price: Decimal
    sale_date: datetime.date
    sale_price: Decimal

    Pythonic = PositionSaleDict

    def __init__(
        self,
        symbol: str,
        quantity: Decimal,
        purchase_date: datetime.date,
        purchase_price: Decimal,
        sale_date: datetime.date,
        sale_price: Decimal,
    ) -> None:
        self.symbol = symbol
        self.quantity = quantity
        self.purchase_date = purchase_date
        self.purchase_price = purchase_price
        self.sale_date = sale_date
        self.sale_price = sale_price

    def profit(self) -> Decimal:
        """
        Calculate the profit from this sale.
        """
        return (self.sale_price - self.purchase_price) * self.quantity

    @property
    def days_held(self) -> int:
        """
        The number of days this position was held
        """
        return (self.sale_date - self.purchase_date).days

    @property
    def investment(self) -> Decimal:
        """
        The amount of money invested
        """
        return self.quantity * self.purchase_price

    def interest(self) -> Decimal:
        """
        Calculate the converted interest of the sale.
        """
        year_percent = (
            Decimal("1")
            if not self.days_held
            else Decimal(self.days_held) / Decimal("365.25")
        )
        return self.profit() / self.investment / year_percent

    @override
    def to_python(self) -> Pythonic:
        """
        Convert this sale to a pythonic ``dict``.
        """
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "purchase_date": self.purchase_date,
            "purchase_price": self.purchase_price,
            "sale_date": self.sale_date,
            "sale_price": self.sale_price,
            "profit": self.profit(),
            "interest": self.interest(),
        }

    @override
    @classmethod
    def from_python(cls, raw: Pythonic) -> "PositionSale":
        """
        Re-create this sale from the given dict. This is effectively the
        opposite of the :meth:`to_python` above.
        """
        return cls(
            raw["symbol"],
            raw["quantity"],
            raw["purchase_date"],
            raw["purchase_price"],
            raw["sale_date"],
            raw["sale_price"],
        )

    @override
    def copy(self) -> "PositionSale":
        """
        Create a copy of this sale.
        """
        return self.__class__(
            self.symbol,
            self.quantity,
            self.purchase_date,
            self.purchase_price,
            self.sale_date,
            self.sale_price,
        )

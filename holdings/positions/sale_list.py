import datetime
from collections.abc import Iterable, Sequence
from decimal import Decimal
from typing import overload

from typing_extensions import override

from holdings.positions.common import Copyable, Pythonable
from holdings.positions.sale import PositionSale

SaleListList = list[PositionSale.Pythonic]


class SaleList(Sequence[PositionSale], Pythonable[SaleListList], Copyable):
    """
    Object representing a list of sales that were made on a position.

    .. automethod:: append
    .. automethod:: clear
    .. automethod:: total_profit
    .. automethod:: average_interest
    """

    Pythonic = SaleListList

    _sales: list[PositionSale]

    def __init__(self, sales: Iterable[PositionSale] | None = None) -> None:
        self._sales = list(sales or [])

    def append(self, sale: PositionSale) -> None:
        """
        Append the given *sale* to this list.
        """
        self._sales.append(sale)

    def extend(self, sales: Iterable[PositionSale]) -> None:
        """
        Extend the given *sales* to this list.
        """
        self._sales.extend(sales)

    def clear(self) -> None:
        """
        Clear out this list of sales
        """
        self._sales = []

    def total_profit(self) -> Decimal:
        """
        Total profit of all contained sales.
        """
        return Decimal(sum(s.profit() for s in self))

    def total_interest(self) -> Decimal:
        """
        Calculate the converted interest of the sale.
        """
        if len(self) == 0:
            return Decimal("0")

        investment_days = Decimal("0")
        start_day = self[0].purchase_date
        end_day = self[-1].sale_date
        day = start_day
        while day < end_day:
            investment_days += Decimal(
                sum(
                    s.investment
                    for s in self
                    if s.purchase_date <= day and s.sale_date > day
                )
            )
            day += datetime.timedelta(days=1)

        total_days = (end_day - start_day).days
        normalized_investment = investment_days / total_days
        year_percent = total_days / Decimal("365.25")
        if normalized_investment == 0 or year_percent == 0:
            return Decimal("0")
        return self.total_profit() / normalized_investment / year_percent

    @override
    def to_python(self) -> Pythonic:
        return [s.to_python() for s in self]

    @override
    @classmethod
    def from_python(cls, raw: Pythonic) -> "SaleList":
        return cls(PositionSale.from_python(r) for r in raw)

    @override
    def copy(self) -> "SaleList":
        return SaleList(s.copy() for s in self)

    @overload
    def __getitem__(self, index: int) -> PositionSale: ...

    @overload
    def __getitem__(self, index: slice) -> "SaleList": ...

    @override
    def __getitem__(self, index: int | slice) -> "PositionSale | SaleList":
        if isinstance(index, slice):
            return SaleList(self._sales[index])
        return self._sales[index]

    @override
    def __len__(self) -> int:
        return len(self._sales)

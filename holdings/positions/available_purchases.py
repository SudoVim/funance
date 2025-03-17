import collections
import datetime
from collections.abc import Iterable, Sequence
from decimal import Decimal

from typing_extensions import overload, override

from holdings.positions.action import PositionAction
from holdings.positions.common import Copyable, Pythonable
from holdings.positions.sale import PositionSale
from holdings.positions.sale_list import SaleList

AvailablePurchasesList = list[PositionAction.Pythonic]


class AvailablePurchases(
    Sequence[PositionAction],
    Pythonable["AvailablePurchasesList"],
    Copyable,
):
    """
    :class:`Sequence` designed for holding and acting on actions that can be
    used pairwise with new "sell" actions to act as the original purchase of
    the ticker.
    """

    Pythonic = AvailablePurchasesList

    _actions: collections.deque[PositionAction]

    def __init__(self, items: Iterable[PositionAction] | None = None) -> None:
        self._actions = collections.deque(items or [])

    def append(self, action: PositionAction) -> None:
        """
        Append the given *action* to this collection.
        """
        self._actions.append(action)

    def offset_sale(
        self, date: datetime.date, price: Decimal, quantity: Decimal
    ) -> SaleList:
        """
        Offset the given sale information with a :class:`SaleList`.
        """

        def get_sales():
            found_quantity = Decimal("0")
            while found_quantity < quantity:
                assert len(self._actions) > 0
                purchase = self._actions[0]
                delta_quantity = min(purchase.quantity, quantity - found_quantity)
                yield PositionSale(
                    purchase.symbol,
                    delta_quantity,
                    purchase.date,
                    purchase.price,
                    date,
                    price,
                )
                purchase.quantity -= delta_quantity
                if purchase.quantity == 0:
                    _ = self._actions.popleft()

        return SaleList(get_sales())

    def add_split(self, new_symbol: str, proportion: Decimal) -> "AvailablePurchases":
        """
        Transform this collection as a split with the given arguments.
        """
        return AvailablePurchases(a.add_split(new_symbol, proportion) for a in self)

    @override
    def to_python(self) -> Pythonic:
        return [a.to_python() for a in self]

    @override
    @classmethod
    def from_python(cls, raw: Pythonic) -> "AvailablePurchases":
        return cls(PositionAction.from_python(r) for r in raw)

    @override
    def copy(self) -> "AvailablePurchases":
        return AvailablePurchases(a.copy() for a in self)

    @overload
    def __getitem__(self, index: int) -> PositionAction: ...

    @overload
    def __getitem__(self, index: slice) -> "AvailablePurchases": ...

    @override
    def __getitem__(self, index: int | slice) -> "PositionAction | AvailablePurchases":
        if isinstance(index, slice):
            return AvailablePurchases(list(self._actions)[index])
        return self._actions[index]

    @override
    def __len__(self) -> int:
        return len(self._actions)

import datetime
from collections.abc import Iterator, Mapping
from decimal import Decimal
from typing import Any

from typing_extensions import override

from holdings.positions.action import PositionAction
from holdings.positions.common import Copyable, Pythonable
from holdings.positions.generation import GenerationType, PositionGeneration
from holdings.positions.position import Position
from holdings.positions.sale_list import SaleList

PositionSetDict = Mapping[str, Position.Pythonic]


class PositionSet(Mapping[str, Position], Pythonable["PositionSetDict"], Copyable):
    """
    A set of positions held by an account.

    .. automethod:: add_buy
    .. automethod:: add_sale
    .. automethod:: add_generation
    .. automethod:: add_split
    .. automethod:: add_distribution
    """

    _positions: dict[str, Position]

    Pythonic = PositionSetDict

    def __init__(self, positions: dict[str, Position] | None = None) -> None:
        self._positions = positions or {}

    def add_buy(
        self,
        symbol: str,
        date: datetime.date,
        quantity: Decimal,
        price: Decimal,
        offset_cash: bool = True,
    ) -> PositionAction | None:
        """
        Add a buy action to this position set
        """
        action = self.ensure_position(symbol).add_buy(date, quantity, price)
        if action is None:
            return None

        if offset_cash:
            _ = self.add_sale(
                "CASH",
                date,
                quantity * price,
                Decimal("1"),
                offset_cash=False,
            )

        return action

    def add_sale(
        self,
        symbol: str,
        date: datetime.date,
        quantity: Decimal,
        price: Decimal,
        offset_cash: bool = True,
    ) -> tuple[PositionAction | None, SaleList]:
        """
        Add a sell action to this position set
        """
        action, sale_list = self.ensure_position(symbol).add_sale(date, quantity, price)
        if action is None:
            return None, SaleList()

        if offset_cash:
            _ = self.add_buy(
                "CASH",
                date,
                quantity * price,
                Decimal("1"),
                offset_cash=False,
            )

        return action, sale_list

    def add_generation(
        self,
        symbol: str,
        date: datetime.date,
        generation_type: GenerationType,
        amount: Decimal,
        offset_cash: bool = True,
    ) -> PositionGeneration | None:
        """
        Add the given *generation* to this set of positions.
        """
        generation = self.ensure_position(symbol).add_generation(
            date, generation_type, amount
        )
        if generation is None:
            return None

        if offset_cash:
            _ = self.add_buy(
                "CASH", date, generation.amount, Decimal("1"), offset_cash=False
            )

        return generation

    def add_split(
        self, from_symbol: str, to_symbol: str, new_quantity: Decimal
    ) -> None:
        """
        Rebalance positions by adding a split.
        """
        position = self._positions[from_symbol]
        self._positions[to_symbol] = position
        del self._positions[from_symbol]

        position.add_split(to_symbol, new_quantity)

    def add_distribution(self, symbol: str, new_shares: Decimal) -> None:
        """
        Add a stock distribution
        """
        self.ensure_position(symbol).add_distribution(new_shares)

    def ensure_position(self, key: str) -> Position:
        if key not in self._positions:
            self._positions[key] = Position(key)
        return self._positions[key]

    @override
    def to_python(self) -> dict[str, Any]:
        return {k: p.to_python() for k, p in self._positions.items()}

    @override
    @classmethod
    def from_python(cls, raw: Pythonic) -> "PositionSet":
        return cls({s: Position.from_python(r) for s, r in raw.items()})

    @override
    def copy(self) -> "PositionSet":
        return self.__class__({k: p.copy() for k, p in self._positions.items()})

    @override
    def __getitem__(self, key: str) -> Position:
        return self._positions.__getitem__(key)

    @override
    def __iter__(self) -> Iterator[str]:
        return self._positions.__iter__()

    @override
    def __len__(self) -> int:
        return self._positions.__len__()

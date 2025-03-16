"""
Module relating to account positions.
"""

import collections
import datetime
from collections.abc import Iterable
from decimal import Decimal
from typing import Any, TypedDict

from holdings.positions.action import PositionAction
from holdings.positions.action_list import ActionList
from holdings.positions.generation import GenerationType, PositionGeneration
from holdings.positions.generation_list import GenerationList
from holdings.positions.sale import PositionSale
from holdings.positions.sale_list import SaleList


class Position:
    """
    A position as part of an account.
    """

    symbol: str
    actions: ActionList
    generations: GenerationList
    quantity: Decimal
    cost_basis: Decimal
    available_purchases: collections.deque[PositionAction]
    sales: SaleList

    class Pythonic(TypedDict):
        symbol: str
        quantity: Decimal
        cost_basis: Decimal
        cost_basis_per_share: Decimal
        actions: ActionList.Pythonic
        generations: GenerationList.Pythonic
        available_purchases: list["PositionAction.Pythonic"]
        sales: SaleList.Pythonic

    def __init__(
        self,
        symbol: str,
        actions: Iterable[PositionAction] | None = None,
        generations: Iterable[PositionGeneration] | None = None,
        quantity: Decimal | None = None,
        cost_basis: Decimal | None = None,
        available_purchases: collections.deque[PositionAction] | None = None,
        sales: Iterable[PositionSale] | None = None,
    ) -> None:
        self.symbol = symbol
        self.actions = ActionList(actions or [])
        self.generations = GenerationList(generations or [])
        self.quantity = quantity or Decimal("0")
        self.cost_basis = cost_basis or Decimal("0")
        self.available_purchases = available_purchases or collections.deque()
        self.sales = SaleList(sales)

    def copy(self) -> "Position":
        """
        Copy this position information.
        """
        return self.__class__(
            self.symbol,
            actions=self.actions.copy(),
            generations=self.generations.copy(),
            quantity=self.quantity,
            cost_basis=self.cost_basis,
            available_purchases=collections.deque(
                a.copy() for a in self.available_purchases
            ),
            sales=collections.deque(s.copy() for s in self.sales),
        )

    def add_action(self, action: PositionAction) -> None:
        """
        Add the given *action* to this position.
        """
        assert self.symbol == action.symbol
        if not self.actions.append(action):
            return

        if action.action == "buy":
            self.available_purchases.append(action.copy())
            self.cost_basis += action.quantity * action.price
            self.quantity += action.quantity
            return

        found_quantity = Decimal("0")
        while found_quantity < action.quantity:
            assert len(self.available_purchases) > 0
            purchase = self.available_purchases[0]
            delta_quantity = min(purchase.quantity, action.quantity - found_quantity)
            self.cost_basis -= delta_quantity * purchase.price
            self.sales.append(
                PositionSale(
                    action.symbol,
                    delta_quantity,
                    purchase.date,
                    purchase.price,
                    action.date,
                    action.price,
                )
            )
            purchase.quantity -= delta_quantity
            if purchase.quantity == 0:
                _ = self.available_purchases.popleft()

            found_quantity += delta_quantity
            self.quantity -= delta_quantity

    def add_generation(
        self,
        date: datetime.date,
        generation_type: GenerationType,
        amount: Decimal,
    ) -> PositionGeneration | None:
        """
        Add a generation with the given parameters to this position.
        """
        generation = PositionGeneration(
            self.symbol,
            date,
            generation_type,
            amount,
            self.cost_basis,
        )
        if not self.generations.append(generation):
            return None
        return generation

    def add_split(self, new_symbol: str, new_quantity: Decimal) -> None:
        """
        Apply a split to this position using the *new_quantity* to determine
        the ratio.
        """
        self.symbol = new_symbol
        proportion = new_quantity / self.quantity
        self.quantity = new_quantity
        self.actions = self.actions.add_split(new_symbol, proportion)
        self.available_purchases = collections.deque(
            a.add_split(new_symbol, proportion) for a in self.available_purchases
        )

    def add_distribution(self, new_shares: Decimal) -> None:
        """
        Apply a distribution to this position using the *new_shares* to
        determine the ratio of the resulting split.
        """
        new_quantity = self.quantity + new_shares
        proportion = new_quantity / self.quantity
        self.quantity = new_quantity
        self.actions = self.actions.add_split(self.symbol, proportion)
        self.available_purchases = collections.deque(
            a.add_split(self.symbol, proportion) for a in self.available_purchases
        )

    def to_python(self) -> dict[str, Any]:
        """
        Convert this position to a pythonic ``dict``
        """
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "cost_basis": self.cost_basis,
            "cost_basis_per_share": (
                Decimal("0") if not self.quantity else self.cost_basis / self.quantity
            ),
            "actions": self.actions.to_python(),
            "generations": [a.to_python() for a in self.generations],
            "available_purchases": [a.to_python() for a in self.available_purchases],
            "sales": [s.to_python() for s in self.sales],
        }

    @classmethod
    def from_python(cls, raw: Pythonic) -> "Position":
        """
        Re-create this sale from the given dict. This is effectively the
        opposite of the :meth:`to_python` above.
        """
        return cls(
            raw["symbol"],
            actions=ActionList.from_python(raw["actions"]),
            generations=[PositionGeneration.from_python(g) for g in raw["generations"]],
            quantity=raw["quantity"],
            cost_basis=raw["cost_basis"],
            available_purchases=collections.deque(
                PositionAction.from_python(a) for a in raw["available_purchases"]
            ),
            sales=SaleList.from_python(raw["sales"]),
        )


class PositionSet:
    """
    A set of positions held by an account.
    """

    positions: dict[str, "Position"]
    latest_date = datetime.date | None

    def __init__(self, positions: dict[str, "Position"] | None = None) -> None:
        self.positions = positions or {}
        self.latest_date = None

    def copy(self) -> "PositionSet":
        """
        Copy this set.
        """
        return self.__class__({k: p.copy() for k, p in self.positions.items()})

    def add_action(self, action: PositionAction, offset_cash: bool = True) -> None:
        """
        Add the given *action* to this set of positions.
        """
        if self.latest_date is None:
            self.latest_date = action.date

        if self.latest_date > action.date:  # pyright: ignore[reportOperatorIssue]
            return

        if action.symbol not in self.positions:
            self.positions[action.symbol] = Position(action.symbol)

        self.positions[action.symbol].add_action(action)
        if offset_cash:
            self.add_action(action.cash_offset(), offset_cash=False)

    def add_generation(
        self,
        symbol: str,
        date: datetime.date,
        generation_type: GenerationType,
        amount: Decimal,
        offset_cash: bool = True,
    ) -> None:
        """
        Add the given *generation* to this set of positions.
        """
        if self.latest_date is None:
            self.latest_date = date

        if self.latest_date > date:  # pyright: ignore[reportOperatorIssue]
            return

        if symbol not in self.positions:
            self.positions[symbol] = Position(symbol)

        generation = self.positions[symbol].add_generation(
            date, generation_type, amount
        )
        if generation and offset_cash:
            self.add_action(generation.cash_offset(), offset_cash=False)

    def add_split(
        self, from_symbol: str, to_symbol: str, new_quantity: Decimal
    ) -> None:
        """
        Rebalance positions by adding a split.
        """
        position = self.positions[from_symbol]
        self.positions[to_symbol] = position
        del self.positions[from_symbol]

        position.add_split(to_symbol, new_quantity)

    def add_distribution(self, symbol: str, new_shares: Decimal) -> None:
        """
        Add a stock distribution
        """
        self.positions[symbol].add_distribution(new_shares)

    def to_python(self) -> dict[str, Any]:
        return {k: p.to_python() for k, p in self.positions.items()}

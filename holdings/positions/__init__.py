"""
Module relating to account positions.
"""

import collections
import datetime
from collections.abc import Iterable
from decimal import Decimal
from typing import Any, Literal, TypedDict

from typing_extensions import override

from holdings.positions.action import PositionAction
from holdings.positions.action_list import ActionList
from holdings.positions.common import Pythonable
from holdings.positions.sale import PositionSale
from holdings.positions.sale_list import SaleList

GenerationType = Literal[
    "dividend",
    "long-term-cap-gain",
    "short-term-cap-gain",
    "interest",
    "royalty-payment",
    "return-of-capital",
    "foreign-tax",
    "fee",
]
GenerationKey = tuple[datetime.date, GenerationType, Decimal]


class PositionGenerationDict(TypedDict):
    symbol: str
    date: datetime.date
    generation_type: GenerationType
    amount: Decimal
    cost_basis: Decimal | None
    percent: Decimal


class PositionGeneration(Pythonable["PositionGenerationDict"]):
    """
    A single instance of wealth generation associated with a symbol
    """

    symbol: str
    date: datetime.date
    generation_type: GenerationType
    amount: Decimal
    cost_basis: Decimal

    Pythonic = PositionGenerationDict

    def __init__(
        self,
        symbol: str,
        date: datetime.date,
        generation_type: GenerationType,
        amount: Decimal,
        cost_basis: Decimal | None = None,
    ) -> None:
        self.symbol = symbol
        self.date = date
        self.generation_type = generation_type
        self.amount = amount
        self.cost_basis = cost_basis or Decimal("0")

    def key(self) -> GenerationKey:
        return self.date, self.generation_type, self.amount

    def copy(self) -> "PositionGeneration":
        return PositionGeneration(
            symbol=self.symbol,
            date=self.date,
            generation_type=self.generation_type,
            amount=self.amount,
            cost_basis=self.cost_basis,
        )

    def cash_offset(self) -> PositionAction:
        """
        Create the cash offset for this generation.
        """
        return PositionAction(
            symbol="CASH",
            date=self.date,
            action="buy",
            quantity=self.amount,
            price=Decimal("1"),
        )

    def position_percentage(self) -> Decimal:
        """
        Calculate the percentage of the position is this generation.
        """
        if self.cost_basis == 0:
            return Decimal("0")

        return self.amount / self.cost_basis

    @classmethod
    def average_interest(
        cls, days: int, generations: list["PositionGeneration"]
    ) -> Decimal:
        """
        Calculate the average interest for the given ``list`` of
        :class:`PositionGeneration` s
        """
        frequency = Decimal(len(generations)) / days * Decimal("365.25")
        average_percentage = Decimal(
            sum((g.position_percentage() * g.cost_basis) for g in generations)
        ) / sum(g.cost_basis for g in generations)
        return average_percentage * frequency

    @override
    def to_python(self) -> Pythonic:
        """
        Convert this generation to a pythonic ``dict``
        """
        return {
            "symbol": self.symbol,
            "date": self.date,
            "generation_type": self.generation_type,
            "amount": self.amount,
            "cost_basis": self.cost_basis,
            "percent": self.position_percentage(),
        }

    @override
    @classmethod
    def from_python(cls, raw: Pythonic) -> "PositionGeneration":
        """
        Re-create this generation from the given dict. This is effectively the
        opposite of the :meth:`to_python` above.
        """
        return cls(
            raw["symbol"],
            raw["date"],
            raw["generation_type"],
            raw["amount"],
            cost_basis=raw["cost_basis"],
        )


class Position:
    """
    A position as part of an account.
    """

    symbol: str
    actions: ActionList
    generations: list["PositionGeneration"]
    generation_index: set["GenerationKey"]
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
        generations: list["PositionGeneration.Pythonic"]
        available_purchases: list["PositionAction.Pythonic"]
        sales: SaleList.Pythonic

    def __init__(
        self,
        symbol: str,
        actions: Iterable[PositionAction] | None = None,
        generations: Iterable["PositionGeneration"] | None = None,
        quantity: Decimal | None = None,
        cost_basis: Decimal | None = None,
        available_purchases: collections.deque[PositionAction] | None = None,
        sales: Iterable[PositionSale] | None = None,
    ) -> None:
        self.symbol = symbol
        self.actions = ActionList(actions or [])
        self.generations = list(generations or [])
        self.generation_index = {g.key() for g in self.generations}
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
            generations=[a.copy() for a in self.generations],
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

    def add_generation(self, generation: "PositionGeneration") -> None:
        """
        Add the given *generation* to this position.
        """
        assert self.symbol == generation.symbol

        if generation.key() in self.generation_index:
            return

        latest_generation = None if len(self.generations) == 0 else self.generations[-1]
        if latest_generation and generation.date < latest_generation.date:
            return

        generation.cost_basis = self.cost_basis
        self.generations.append(generation)
        self.generation_index.add(generation.key())

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
        self, generation: "PositionGeneration", offset_cash: bool = True
    ) -> None:
        """
        Add the given *generation* to this set of positions.
        """
        if self.latest_date is None:
            self.latest_date = generation.date

        if self.latest_date > generation.date:  # pyright: ignore[reportOperatorIssue]
            return

        if generation.symbol not in self.positions:
            self.positions[generation.symbol] = Position(generation.symbol)

        self.positions[generation.symbol].add_generation(generation)
        if offset_cash:
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

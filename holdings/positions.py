"""
Module relating to account positions.
"""

import collections
import datetime
from decimal import Decimal
from typing import Any, Literal


Action = Literal["buy", "sell"]
ActionKey = tuple[datetime.date, Action, Decimal, Decimal]


class PositionSale:
    """
    Object representing the sale of a position.
    """

    symbol: str
    quantity: Decimal
    purchase_date: datetime.date
    purchase_price: Decimal
    sale_date: datetime.date
    sale_price: Decimal

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

    def profit(self) -> Decimal:
        """
        Calculate the profit from this sale.
        """
        return (self.sale_price - self.purchase_price) * self.quantity

    def interest(self) -> Decimal:
        """
        Calculate the converted interest of the sale.
        """
        days = Decimal((self.sale_date - self.purchase_date).days)
        year_percent = Decimal("1") if not days else days / Decimal("365.25")
        return self.profit() / self.quantity / self.purchase_price / year_percent

    @classmethod
    def average_interest(cls, sales: list["PositionSale"]) -> Decimal:
        """
        Calculate the average interest for the given ``list`` of
        :class:`PositionSale` s
        """
        return Decimal(sum([(s.interest() * s.profit()) for s in sales])) / sum(
            [s.profit() for s in sales]
        )

    def to_python(self) -> dict:
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


class PositionAction:
    """
    A single action for a position held in an account.
    """

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

    def key(self) -> ActionKey:
        return self.date, self.action, self.quantity, self.price

    def copy(self) -> "PositionAction":
        return PositionAction(
            symbol=self.symbol,
            date=self.date,
            action=self.action,
            quantity=self.quantity,
            price=self.price,
        )

    def cash_offset(self) -> "PositionAction":
        """
        Create the cash offset for this action.
        """
        return self.__class__(
            symbol="CASH",
            date=self.date,
            action="sell" if self.action == "buy" else "buy",
            quantity=self.quantity * self.price,
            price=Decimal("1"),
        )

    def add_split(self, new_symbol: str, proportion: Decimal) -> "PositionAction":
        """
        Recalculate this action after a split.
        """
        return self.__class__(
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

    def to_python(self) -> dict[str, Any]:
        """
        Convert this action to a pythonic ``dict``
        """
        return {
            "symbol": self.symbol,
            "date": self.date,
            "action": self.action,
            "quantity": self.quantity,
            "price": self.price,
            "total": self.quantity * self.price,
        }


GenerationType = Literal[
    "dividend",
    "long-term-cap-gain",
    "short-term-cap-gain",
    "interest",
    "distribution",
    "royalty-payment",
    "return-of-capital",
    "foreign-tax",
    "fee",
]
GenerationKey = tuple[datetime.date, GenerationType, Decimal]


class PositionGeneration:
    """
    A single instance of wealth generation associated with a symbol
    """

    symbol: str
    date: datetime.date
    generation_type: GenerationType
    amount: Decimal
    cost_basis: Decimal

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

    def cash_offset(self) -> "PositionAction":
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

    def to_python(self) -> dict[str, Any]:
        """
        Convert this generation to a pythonic ``dict``
        """
        return {
            "symbol": self.symbol,
            "date": self.date,
            "generation_type": self.generation_type,
            "amount": self.amount,
            "percent": self.position_percentage(),
        }


class Position:
    """
    A position as part of an account.
    """

    symbol: str
    actions: list["PositionAction"]
    action_index: set[ActionKey]
    generations: list["PositionGeneration"]
    generation_index: set["GenerationKey"]
    quantity: Decimal
    cost_basis: Decimal
    available_purchases: collections.deque["PositionAction"]
    sales: collections.deque["PositionSale"]

    def __init__(
        self,
        symbol: str,
        actions: list["PositionAction"] | None = None,
        action_index: set[ActionKey] | None = None,
        generations: list["PositionGeneration"] | None = None,
        generation_index: set[GenerationKey] | None = None,
        quantity: Decimal | None = None,
        cost_basis: Decimal | None = None,
        available_purchases: collections.deque["PositionAction"] | None = None,
        sales: collections.deque["PositionSale"] | None = None,
    ) -> None:
        self.symbol = symbol
        self.actions = actions or []
        self.action_index = action_index or set()
        self.generations = generations or []
        self.generation_index = generation_index or set()
        self.quantity = quantity or Decimal("0")
        self.cost_basis = cost_basis or Decimal("0")
        self.available_purchases = available_purchases or collections.deque()
        self.sales = sales or collections.deque()

    def copy(self) -> "Position":
        """
        Copy this position information.
        """
        return self.__class__(
            self.symbol,
            actions=[a.copy() for a in self.actions],
            action_index={k for k in self.action_index},
            generations=[a.copy() for a in self.generations],
            generation_index={k for k in self.generation_index},
            quantity=self.quantity,
            cost_basis=self.cost_basis,
            available_purchases=collections.deque(
                a.copy() for a in self.available_purchases
            ),
            sales=collections.deque(s.copy() for s in self.sales),
        )

    def add_action(self, action: "PositionAction") -> None:
        """
        Add the given *action* to this position.
        """
        assert self.symbol == action.symbol

        if action.key() in self.action_index:
            return

        latest_action = None if len(self.actions) == 0 else self.actions[-1]
        if latest_action and action.date < latest_action.date:
            return

        self.actions.append(action)
        self.action_index.add(action.key())
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
                self.available_purchases.popleft()

            found_quantity += delta_quantity
            self.quantity -= delta_quantity

    def add_generation(self, generation: "PositionGeneration") -> None:
        """
        Add the given *generation* to this position.
        """
        assert self.symbol == generation.symbol

        if generation.key() in self.generation_index:
            return

        latest_action = None if len(self.actions) == 0 else self.actions[-1]
        if latest_action and generation.date < latest_action.date:
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
        self.actions = [a.add_split(new_symbol, proportion) for a in self.actions]
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
        self.actions = [a.add_split(self.symbol, proportion) for a in self.actions]
        self.available_purchases = collections.deque(
            a.add_split(self.symbol, proportion) for a in self.available_purchases
        )

    def to_python(self) -> dict[str, Any]:
        """
        Convert this position to a pythonic ``dict``
        """
        return {
            "quantity": self.quantity,
            "cost_basis": self.cost_basis,
            "cost_basis_per_share": (
                Decimal("0") if not self.quantity else self.cost_basis / self.quantity
            ),
            "actions": [a.to_python() for a in self.actions],
            "generations": [a.to_python() for a in self.generations],
            "sales": [s.to_python() for s in self.sales],
        }


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

    def add_action(self, action: "PositionAction", offset_cash: bool = True) -> None:
        """
        Add the given *action* to this set of positions.
        """
        if self.latest_date is None:
            self.latest_date = action.date

        if self.latest_date > action.date:  # pyright: ignore
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

        if self.latest_date > generation.date:  # pyright: ignore
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

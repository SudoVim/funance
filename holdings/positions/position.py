import datetime
from collections.abc import Iterable
from decimal import Decimal
from typing import TypedDict

from typing_extensions import override

from holdings.positions.action import PositionAction
from holdings.positions.action_list import ActionList
from holdings.positions.available_purchases import AvailablePurchases
from holdings.positions.common import Copyable, Pythonable
from holdings.positions.generation import GenerationType, PositionGeneration
from holdings.positions.generation_list import GenerationList
from holdings.positions.sale import PositionSale
from holdings.positions.sale_list import SaleList


class PositionDict(TypedDict):
    symbol: str
    quantity: Decimal
    cost_basis: Decimal
    cost_basis_per_share: Decimal
    actions: ActionList.Pythonic
    generations: GenerationList.Pythonic
    available_purchases: AvailablePurchases.Pythonic
    sales: SaleList.Pythonic


AddBuyResponse = PositionAction | None
AddSaleResponse = tuple[AddBuyResponse, SaleList]
AddGenerationResponse = PositionGeneration | None


class Position(Pythonable["PositionDict"], Copyable):
    """
    A position as part of an account.
    """

    symbol: str
    actions: ActionList
    generations: GenerationList
    quantity: Decimal
    cost_basis: Decimal
    available_purchases: AvailablePurchases
    sales: SaleList

    Pythonic = PositionDict

    def __init__(
        self,
        symbol: str,
        actions: Iterable[PositionAction] | None = None,
        generations: Iterable[PositionGeneration] | None = None,
        quantity: Decimal | None = None,
        cost_basis: Decimal | None = None,
        available_purchases: Iterable[PositionAction] | None = None,
        sales: Iterable[PositionSale] | None = None,
    ) -> None:
        self.symbol = symbol
        self.actions = ActionList(actions or [])
        self.generations = GenerationList(generations or [])
        self.quantity = quantity or Decimal("0")
        self.cost_basis = cost_basis or Decimal("0")
        self.available_purchases = AvailablePurchases(available_purchases or [])
        self.sales = SaleList(sales)

    def add_buy(
        self, date: datetime.date, quantity: Decimal, price: Decimal
    ) -> AddBuyResponse:
        """
        Add a buy action with the given inputs
        """
        action = PositionAction(self.symbol, date, "buy", quantity, price)
        if not self.actions.append(action):
            return None

        self.available_purchases.append(action.copy())
        self.cost_basis += action.quantity * action.price
        self.quantity += action.quantity
        return action

    def assert_add_buy(
        self, date: datetime.date, quantity: Decimal, price: Decimal
    ) -> PositionAction:
        """
        Add a buy action with the given inputs and assert that it was added
        """
        action = self.add_buy(date, quantity, price)
        if action is None:
            raise ValueError("Buy action was added out of order")

        return action

    def add_sale(
        self, date: datetime.date, quantity: Decimal, price: Decimal
    ) -> AddSaleResponse:
        """
        Add a sell action with the given inputs
        """
        action = PositionAction(self.symbol, date, "sell", quantity, price)
        if not self.actions.append(action):
            return None, SaleList()

        sales = self.available_purchases.offset_sale(date, price, quantity)
        for sale in sales:
            self.cost_basis -= sale.quantity * sale.purchase_price
            self.quantity -= sale.quantity

        return action, sales

    def assert_add_sale(
        self, date: datetime.date, quantity: Decimal, price: Decimal
    ) -> tuple[PositionAction, SaleList]:
        """
        Add a sell action with the given inputs and assert that it was added
        """
        action, sale_list = self.add_sale(date, quantity, price)
        if action is None:
            raise ValueError("Sell action was added out of order")

        return action, sale_list

    def add_generation(
        self,
        date: datetime.date,
        generation_type: GenerationType,
        amount: Decimal,
    ) -> AddGenerationResponse:
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
        self.available_purchases = self.available_purchases.add_split(
            new_symbol, proportion
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
        self.available_purchases = self.available_purchases.add_split(
            self.symbol, proportion
        )

    @override
    def to_python(self) -> Pythonic:
        return {
            "symbol": self.symbol,
            "quantity": self.quantity,
            "cost_basis": self.cost_basis,
            "cost_basis_per_share": (
                Decimal("0") if not self.quantity else self.cost_basis / self.quantity
            ),
            "actions": self.actions.to_python(),
            "generations": self.generations.to_python(),
            "available_purchases": self.available_purchases.to_python(),
            "sales": self.sales.to_python(),
        }

    @override
    @classmethod
    def from_python(cls, raw: Pythonic) -> "Position":
        return cls(
            raw["symbol"],
            actions=ActionList.from_python(raw["actions"]),
            generations=[PositionGeneration.from_python(g) for g in raw["generations"]],
            quantity=raw["quantity"],
            cost_basis=raw["cost_basis"],
            available_purchases=AvailablePurchases.from_python(
                raw["available_purchases"]
            ),
            sales=SaleList.from_python(raw["sales"]),
        )

    @override
    def copy(self) -> "Position":
        return self.__class__(
            self.symbol,
            actions=self.actions.copy(),
            generations=self.generations.copy(),
            quantity=self.quantity,
            cost_basis=self.cost_basis,
            available_purchases=self.available_purchases.copy(),
            sales=self.sales.copy(),
        )

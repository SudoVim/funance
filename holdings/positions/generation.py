import datetime
from decimal import Decimal
from typing import Literal, TypedDict

from typing_extensions import override

from holdings.positions.action import PositionAction
from holdings.positions.common import Copyable, Pythonable
from holdings.positions.unique import Unique

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
    cost_basis: Decimal
    percent: Decimal


class PositionGeneration(Pythonable["PositionGenerationDict"], Copyable, Unique):
    """
    A single instance of wealth generation associated with a symbol

    .. automethod:: cash_offset
    .. automethod:: position_percentage
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
        cost_basis: Decimal,
    ) -> None:
        self.symbol = symbol
        self.date = date
        self.generation_type = generation_type
        self.amount = amount
        self.cost_basis = cost_basis

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

    @override
    def to_python(self) -> Pythonic:
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
        return cls(
            raw["symbol"],
            raw["date"],
            raw["generation_type"],
            raw["amount"],
            cost_basis=raw["cost_basis"],
        )

    @override
    def key(self) -> GenerationKey:
        return self.date, self.generation_type, self.amount

    @override
    def copy(self) -> "PositionGeneration":
        return PositionGeneration(
            symbol=self.symbol,
            date=self.date,
            generation_type=self.generation_type,
            amount=self.amount,
            cost_basis=self.cost_basis,
        )

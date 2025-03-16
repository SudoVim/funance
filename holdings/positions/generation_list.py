from decimal import Decimal

from typing_extensions import Self, override

from holdings.positions.common import Copyable, Pythonable
from holdings.positions.generation import PositionGeneration
from holdings.positions.unique import UniqueList

PositionGenerationList = list[PositionGeneration.Pythonic]


class GenerationList(
    UniqueList["PositionGeneration"],
    Pythonable["PositionGenerationList"],
    Copyable,
):
    """
    Abstraction for operations that can be performed on a ``list`` of
    :class:`PositionGeneration` s.
    """

    Pythonic = PositionGenerationList

    def average_interest(self, days: int) -> Decimal:
        """
        Calculate the average interest for our :class:`PositionGeneration` s.
        """
        frequency = Decimal(len(self)) / days * Decimal("365.25")
        average_percentage = Decimal(
            sum((g.position_percentage() * g.cost_basis) for g in self)
        ) / sum(g.cost_basis for g in self)
        return average_percentage * frequency

    @override
    def append(self, item: PositionGeneration) -> bool:
        """
        Append the given generation to this list taking into account whether or
        not we've already progressed past the date that this generation was
        created. Return whether or not it was appended.
        """
        latest_generation = None if len(self) == 0 else self[-1]
        if latest_generation and item.date < latest_generation.date:
            return False

        return super().append(item)

    @classmethod
    @override
    def from_python(cls, raw: "GenerationList.Pythonic") -> Self:
        return cls(PositionGeneration.from_python(a) for a in raw)

    @override
    def to_python(self) -> "GenerationList.Pythonic":
        return [a.to_python() for a in self]

    @override
    def copy(self) -> "GenerationList":
        return GenerationList(a.copy() for a in self)

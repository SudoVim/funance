from decimal import Decimal

from typing_extensions import Self, override

from holdings.positions.action import PositionAction
from holdings.positions.common import Copyable, Pythonable
from holdings.positions.unique import UniqueList

PositionActionList = list[PositionAction.Pythonic]


class ActionList(
    UniqueList["PositionAction"],
    Pythonable["PositionActionList"],
    Copyable,
):
    """
    Abstraction for operations that can be performed on a ``list`` of
    :class:`PositionAction` s.
    """

    Pythonic = PositionActionList

    def add_split(self, new_symbol: str, proportion: Decimal) -> "ActionList":
        """
        Apply a split to this position using the given *proportion*
        """
        return ActionList(a.add_split(new_symbol, proportion) for a in self)

    def net_cost_basis(self) -> Decimal:
        """
        Calculate the net cost basis of contained actions
        """

        def iterate_cost_basis():
            for action in self:
                if action.action == "buy":
                    yield action.cost_basis()
                    continue
                yield -action.cost_basis()

        return Decimal(sum(iterate_cost_basis()))

    @override
    def append(self, item: PositionAction) -> bool:
        latest_action = None if len(self) == 0 else self[-1]
        if latest_action and item.date < latest_action.date:
            return False

        return super().append(item)

    @classmethod
    @override
    def from_python(cls, raw: "ActionList.Pythonic") -> Self:
        return cls(PositionAction.from_python(a) for a in raw)

    @override
    def to_python(self) -> "ActionList.Pythonic":
        return [a.to_python() for a in self]

    @override
    def copy(self) -> "ActionList":
        return ActionList(a.copy() for a in self)

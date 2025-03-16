from abc import ABC, abstractmethod
from collections.abc import Iterable, Sequence
from typing import Any, Generic, TypeVar, overload

from typing_extensions import Self, override


class Unique(ABC):
    """
    Abstract base class for defining an object that is considered unique.
    """

    @abstractmethod
    def key(self) -> tuple[Any, ...]:
        """
        Object providing uniqueness to this object.
        """


U = TypeVar("U", bound=Unique)


class UniqueList(Sequence[U], Generic[U]):
    """
    ``list`` that only appends items that aren't already included

    .. automethod:: append
    .. automethod:: clear
    """

    _items: list[U]
    _item_keys: set[tuple[Any, ...]]

    def __init__(self, items: Iterable[U] | None = None) -> None:
        self._items = list(items or [])
        self._item_keys = set(i.key() for i in self._items)

    def append(self, item: U) -> bool:
        """
        Append the given *item* to the list and return whether or not it was
        successfully appended.
        """
        if item.key() in self._item_keys:
            return False
        self._items.append(item)
        self._item_keys.add(item.key())
        return True

    def clear(self) -> None:
        """
        Clear out this list of items
        """
        self._items = []
        self._item_keys = set()

    @overload
    def __getitem__(self, index: int) -> U: ...

    @overload
    def __getitem__(self, index: slice) -> Self: ...

    @override
    def __getitem__(self, index: int | slice) -> U | Self:
        if isinstance(index, slice):
            return self.__class__(self._items[index])
        return self._items[index]

    @override
    def __len__(self) -> int:
        return len(self._items)

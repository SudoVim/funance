from abc import ABC, abstractmethod
from typing import Generic, TypeVar

from typing_extensions import Self

D = TypeVar("D")


class Pythonable(ABC, Generic[D]):
    """
    Abstract base class for defining an object that can translate itself to
    an object and take that same object to recreate itself.
    """

    @abstractmethod
    def to_python(self) -> D:
        """
        Convert this object to a pythonic object.
        """

    @classmethod
    @abstractmethod
    def from_python(cls, raw: D) -> Self:
        """
        Re-create this object from the given object. This is effectively the
        opposite of the :meth:`to_python` above.
        """


class Copyable(ABC):
    """
    Abstract base class for defining an object that can produce a copy of
    itself.
    """

    @abstractmethod
    def copy(self) -> Self:
        """
        Return a copy of this action.
        """

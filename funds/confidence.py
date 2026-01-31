from collections.abc import Iterable, Sequence
from decimal import Decimal

from typing_extensions import Self, overload, override


class Confidence:
    """
    A single datapoint used when calculating confidence containing the
    component parts.

    .. autoattribute:: confidence
    .. autoattribute:: max_confidence_shares
    .. autoattribute:: value_percent
    .. autoattribute:: confidence_shares
    """

    #: The percent confidence (integer 0-100)
    confidence: int

    #: The maximum amount of confidence represented
    max_confidence_shares: int

    #: The percent of the whole represented by this position
    value_percent: Decimal

    def __init__(
        self, confidence: int, max_confidence_shares: int, value_percent: Decimal
    ) -> None:
        self.confidence = confidence
        self.max_confidence_shares = max_confidence_shares
        self.value_percent = value_percent

    @property
    def confidence_shares(self) -> Decimal:
        """
        The number of shares represented
        """
        return (
            Decimal(self.confidence)
            * self.max_confidence_shares
            * self.value_percent
            / 100
        )

    @classmethod
    def weekly(cls, confidence: int, value_percent: Decimal) -> Self:
        """
        Generate a weekly :class:`Confidence`
        """
        return cls(
            confidence,
            1,
            value_percent,
        )

    @classmethod
    def monthly(cls, confidence: int, value_percent: Decimal) -> Self:
        """
        Generate a monthly :class:`Confidence`
        """
        return cls(
            confidence,
            2,
            value_percent,
        )

    @classmethod
    def quarterly(cls, confidence: int, value_percent: Decimal) -> Self:
        """
        Generate a quarterly :class:`Confidence`
        """
        return cls(
            confidence,
            4,
            value_percent,
        )

    def apply_percentage(self, value_percent: Decimal) -> Self:
        return self.__class__(
            self.confidence,
            self.max_confidence_shares,
            value_percent * value_percent,
        )


class ConfidenceList(Sequence[Confidence]):
    _confidences: list[Confidence]

    def __init__(self, confidences: Iterable[Confidence] | None = None) -> None:
        self._confidences = list(confidences or [])

    @property
    def max_confidence_shares(self) -> Decimal:
        return Decimal(
            sum(
                Decimal(c.max_confidence_shares) * c.value_percent
                for c in self._confidences
            )
        )

    @property
    def confidence_shares(self) -> Decimal:
        return Decimal(
            sum(c.confidence_shares for c in self._confidences),
        )

    @property
    def confidence(self) -> Decimal:
        if not self.max_confidence_shares:
            return Decimal("0")
        return self.confidence_shares / self.max_confidence_shares

    @override
    def __len__(self) -> int:
        return self._confidences.__len__()

    @overload
    def __getitem__(self, index: int) -> Confidence: ...

    @overload
    def __getitem__(self, index: slice) -> Self: ...

    @override
    def __getitem__(self, index: int | slice) -> Confidence | Self:
        if isinstance(index, slice):
            return self.__class__(self._confidences[index])
        return self._confidences[index]

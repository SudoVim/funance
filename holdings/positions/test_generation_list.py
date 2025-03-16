import datetime
from decimal import Decimal
from unittest import TestCase

from holdings.positions.generation import PositionGeneration
from holdings.positions.generation_list import GenerationList


class GenerationListTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None
        self.list = GenerationList(
            [
                PositionGeneration(
                    "AAPL",
                    datetime.date(2025, 2, 16),
                    "dividend",
                    Decimal("18.00"),
                    Decimal("234.56"),
                ),
                PositionGeneration(
                    "AAPL",
                    datetime.date(2025, 3, 16),
                    "dividend",
                    Decimal("20.00"),
                    Decimal("234.56"),
                ),
            ],
        )


class AverageInterestTests(GenerationListTestCase):
    def test(self) -> None:
        self.assertEqual(
            Decimal("0.5917249317871759890859481583"), self.list.average_interest(100)
        )

    def test_slice(self) -> None:
        self.assertEqual(
            Decimal("0.2802907571623465211459754434"),
            self.list[:1].average_interest(100),
        )


class AppendTests(GenerationListTestCase):
    def test(self) -> None:
        self.assertEqual(
            True,
            self.list.append(
                PositionGeneration(
                    "AAPL",
                    datetime.date(2025, 4, 16),
                    "dividend",
                    Decimal("20.00"),
                    Decimal("234.56"),
                ),
            ),
        )
        self.assertEqual(3, len(self.list))

    def test_in_past(self) -> None:
        self.assertEqual(
            False,
            self.list.append(
                PositionGeneration(
                    "AAPL",
                    datetime.date(2025, 2, 16),
                    "dividend",
                    Decimal("20.00"),
                    Decimal("234.56"),
                ),
            ),
        )
        self.assertEqual(2, len(self.list))

import datetime
from decimal import Decimal
from unittest import TestCase

from holdings.positions.generation import PositionGeneration


class PositionGenerationTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None
        self.generation = PositionGeneration(
            "AAPL",
            datetime.date(2025, 3, 16),
            "dividend",
            Decimal("20.00"),
            Decimal("234.56"),
        )


class CashOffsetTests(PositionGenerationTestCase):
    def test(self) -> None:
        self.assertEqual(
            {
                "action": "buy",
                "date": datetime.date(2025, 3, 16),
                "price": Decimal("1"),
                "quantity": Decimal("20.00"),
                "symbol": "CASH",
                "total": Decimal("20.00"),
            },
            self.generation.cash_offset().to_python(),
        )


class PositionPercentageTests(PositionGenerationTestCase):
    def test(self) -> None:
        self.assertEqual(
            Decimal("0.08526603001364256480218281037"),
            self.generation.position_percentage(),
        )

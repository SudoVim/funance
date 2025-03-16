import datetime
from decimal import Decimal
from unittest import TestCase

from holdings.positions.sale import PositionSale
from holdings.positions.sale_list import SaleList


class SaleListTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.list = SaleList(
            [
                PositionSale(
                    "AAPL",
                    Decimal("3"),
                    datetime.date(2024, 3, 16),
                    Decimal("200.00"),
                    datetime.date(2025, 3, 16),
                    Decimal("234.56"),
                ),
                PositionSale(
                    "AAPL",
                    Decimal("3"),
                    datetime.date(2024, 9, 16),
                    Decimal("220.00"),
                    datetime.date(2025, 3, 16),
                    Decimal("234.56"),
                ),
            ]
        )


class AverageInterestTests(SaleListTestCase):
    def test(self) -> None:
        self.assertEqual(
            Decimal("0.1612494966414502672225362173"), self.list.average_interest()
        )

    def test_slice(self) -> None:
        self.assertEqual(
            Decimal("0.1729183561643835616438356164"), self.list[:1].average_interest()
        )

    def test_slice_2(self) -> None:
        self.assertEqual(
            Decimal("0.1335519839276745354093420392"), self.list[1:].average_interest()
        )

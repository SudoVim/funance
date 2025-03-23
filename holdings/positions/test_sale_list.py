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


class TotalInterestTests(SaleListTestCase):
    def test(self) -> None:
        self.assertEqual(
            Decimal("0.1590239319269633043786562666"), self.list.total_interest()
        )

    def test_slice(self) -> None:
        self.assertEqual(
            Decimal("0.1729183561643835616438356164"), self.list[:1].total_interest()
        )

    def test_slice_2(self) -> None:
        self.assertEqual(
            Decimal("0.1335519839276745354093420392"), self.list[1:].total_interest()
        )

    def test_real(self) -> None:
        cmp_list = SaleList(
            [
                PositionSale(
                    "AMD",
                    Decimal("2"),
                    datetime.date(2023, 4, 13),
                    Decimal("92.60000000"),
                    datetime.date(2023, 5, 31),
                    Decimal("119.60000000"),
                ),
                PositionSale(
                    "AMD",
                    Decimal("2"),
                    datetime.date(2023, 6, 15),
                    Decimal("125.06000000"),
                    datetime.date(2023, 8, 31),
                    Decimal("105.35000000"),
                ),
                PositionSale(
                    "AMD",
                    Decimal("4"),
                    datetime.date(2023, 5, 9),
                    Decimal("95.67000000"),
                    datetime.date(2023, 8, 31),
                    Decimal("105.35000000"),
                ),
            ]
        )

        self.assertEqual(
            Decimal("0.2712364833347173001612274913"), cmp_list.total_interest()
        )


class CopyTests(SaleListTestCase):
    def test(self) -> None:
        cmp_list = self.list.copy()
        self.assertEqual(self.list.to_python(), cmp_list.to_python())

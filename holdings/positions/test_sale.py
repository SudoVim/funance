import datetime
from decimal import Decimal
from unittest import TestCase

from holdings.positions.sale import PositionSale


class PositionSaleTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.sale = PositionSale(
            "AAPL",
            Decimal("3"),
            datetime.date(2024, 3, 16),
            Decimal("200.00"),
            datetime.date(2025, 3, 16),
            Decimal("234.56"),
        )


class ProfitTests(PositionSaleTestCase):
    def test(self) -> None:
        self.assertEqual(Decimal("103.68"), self.sale.profit())


class InterestTests(PositionSaleTestCase):
    def test(self) -> None:
        self.assertEqual(
            Decimal("0.1729183561643835616438356164"), self.sale.interest()
        )

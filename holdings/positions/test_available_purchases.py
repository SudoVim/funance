import datetime
from decimal import Decimal
from unittest import TestCase

from holdings.positions.action import PositionAction
from holdings.positions.available_purchases import AvailablePurchases


class AvailablePurchasesTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.available_purchases = AvailablePurchases()


class AppendTests(AvailablePurchasesTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.buy_action = PositionAction(
            "AAPL",
            datetime.date(2025, 3, 17),
            "buy",
            Decimal("4"),
            Decimal("213.49"),
        )

    def test(self) -> None:
        self.available_purchases.append(self.buy_action)
        self.assertEqual(
            [
                {
                    "action": "buy",
                    "date": datetime.date(2025, 3, 17),
                    "price": Decimal("213.49"),
                    "quantity": Decimal("4"),
                    "symbol": "AAPL",
                    "total": Decimal("853.96"),
                }
            ],
            self.available_purchases.to_python(),
        )


class OffsetSaleTests(AvailablePurchasesTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.buy_action = PositionAction(
            "AAPL",
            datetime.date(2025, 3, 17),
            "buy",
            Decimal("4"),
            Decimal("213.49"),
        )
        self.available_purchases.append(self.buy_action)

    def test(self) -> None:
        cmp_sale_list = self.available_purchases.offset_sale(
            datetime.date(2025, 3, 18),
            Decimal("220.49"),
            Decimal("2"),
        )
        self.assertEqual(
            [
                {
                    "interest": Decimal("11.97597077146470560681999157"),
                    "profit": Decimal("14.00"),
                    "purchase_date": datetime.date(2025, 3, 17),
                    "purchase_price": Decimal("213.49"),
                    "quantity": Decimal("2"),
                    "sale_date": datetime.date(2025, 3, 18),
                    "sale_price": Decimal("220.49"),
                    "symbol": "AAPL",
                },
            ],
            cmp_sale_list.to_python(),
        )
        self.assertEqual(
            [
                {
                    "action": "buy",
                    "date": datetime.date(2025, 3, 17),
                    "price": Decimal("213.49"),
                    "quantity": Decimal("2"),
                    "symbol": "AAPL",
                    "total": Decimal("426.98"),
                }
            ],
            self.available_purchases.to_python(),
        )

    def test_empty(self) -> None:
        cmp_sale_list = self.available_purchases.offset_sale(
            datetime.date(2025, 3, 18),
            Decimal("220.49"),
            Decimal("4"),
        )
        self.assertEqual(
            [
                {
                    "interest": Decimal("11.97597077146470560681999157"),
                    "profit": Decimal("28.00"),
                    "purchase_date": datetime.date(2025, 3, 17),
                    "purchase_price": Decimal("213.49"),
                    "quantity": Decimal("4"),
                    "sale_date": datetime.date(2025, 3, 18),
                    "sale_price": Decimal("220.49"),
                    "symbol": "AAPL",
                },
            ],
            cmp_sale_list.to_python(),
        )
        self.assertEqual([], self.available_purchases.to_python())

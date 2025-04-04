import datetime
from decimal import Decimal
from unittest import TestCase

from holdings.positions.position_set import PositionSet


class PositionSetTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None
        self.position_set = PositionSet()


class AddBuyTests(PositionSetTestCase):
    def test(self) -> None:
        self.position_set.add_buy(
            "AAPL",
            datetime.date(2025, 3, 18),
            Decimal("4"),
            Decimal("212.29"),
        )
        self.assertEqual(
            {
                "AAPL": {
                    "actions": [
                        {
                            "action": "buy",
                            "date": datetime.date(2025, 3, 18),
                            "price": Decimal("212.29"),
                            "quantity": Decimal("4"),
                            "symbol": "AAPL",
                            "total": Decimal("849.16"),
                        },
                    ],
                    "available_purchases": [
                        {
                            "action": "buy",
                            "date": datetime.date(2025, 3, 18),
                            "price": Decimal("212.29"),
                            "quantity": Decimal("4"),
                            "symbol": "AAPL",
                            "total": Decimal("849.16"),
                        },
                    ],
                    "cost_basis": Decimal("849.16"),
                    "cost_basis_per_share": Decimal("212.29"),
                    "generations": [],
                    "quantity": Decimal("4"),
                    "sales": [],
                    "symbol": "AAPL",
                },
            },
            self.position_set.to_python(),
        )


class AddSaleTests(PositionSetTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.position_set.add_buy(
            "AAPL",
            datetime.date(2025, 3, 18),
            Decimal("4"),
            Decimal("212.29"),
        )

    def test(self) -> None:
        self.position_set.add_sale(
            "AAPL",
            datetime.date(2025, 3, 19),
            Decimal("2"),
            Decimal("220.29"),
        )
        self.assertEqual(
            {
                "AAPL": {
                    "actions": [
                        {
                            "action": "buy",
                            "date": datetime.date(2025, 3, 18),
                            "price": Decimal("212.29"),
                            "quantity": Decimal("4"),
                            "symbol": "AAPL",
                            "total": Decimal("849.16"),
                        },
                        {
                            "action": "sell",
                            "date": datetime.date(2025, 3, 19),
                            "price": Decimal("220.29"),
                            "quantity": Decimal("2"),
                            "symbol": "AAPL",
                            "total": Decimal("440.58"),
                        },
                    ],
                    "available_purchases": [
                        {
                            "action": "buy",
                            "date": datetime.date(2025, 3, 18),
                            "price": Decimal("212.29"),
                            "quantity": Decimal("2"),
                            "symbol": "AAPL",
                            "total": Decimal("424.58"),
                        },
                    ],
                    "cost_basis": Decimal("424.58"),
                    "cost_basis_per_share": Decimal("212.29"),
                    "generations": [],
                    "quantity": Decimal("2"),
                    "sales": [
                        {
                            "interest": Decimal("13.76419049413538084695463752"),
                            "profit": Decimal("16.00"),
                            "purchase_date": datetime.date(2025, 3, 18),
                            "purchase_price": Decimal("212.29"),
                            "quantity": Decimal("2"),
                            "sale_date": datetime.date(2025, 3, 19),
                            "sale_price": Decimal("220.29"),
                            "symbol": "AAPL",
                        },
                    ],
                    "symbol": "AAPL",
                },
            },
            self.position_set.to_python(),
        )


class AddGenerationTests(PositionSetTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.position_set.add_buy(
            "AAPL",
            datetime.date(2025, 3, 18),
            Decimal("4"),
            Decimal("212.29"),
        )

    def test(self) -> None:
        self.position_set.add_generation(
            "AAPL",
            datetime.date(2025, 3, 19),
            "dividend",
            Decimal("20.00"),
        )
        self.assertEqual(
            {
                "AAPL": {
                    "actions": [
                        {
                            "action": "buy",
                            "date": datetime.date(2025, 3, 18),
                            "price": Decimal("212.29"),
                            "quantity": Decimal("4"),
                            "symbol": "AAPL",
                            "total": Decimal("849.16"),
                        },
                    ],
                    "available_purchases": [
                        {
                            "action": "buy",
                            "date": datetime.date(2025, 3, 18),
                            "price": Decimal("212.29"),
                            "quantity": Decimal("4"),
                            "symbol": "AAPL",
                            "total": Decimal("849.16"),
                        },
                    ],
                    "cost_basis": Decimal("849.16"),
                    "cost_basis_per_share": Decimal("212.29"),
                    "generations": [
                        {
                            "amount": Decimal("20.00"),
                            "cost_basis": Decimal("849.16"),
                            "date": datetime.date(2025, 3, 19),
                            "generation_type": "dividend",
                            "percent": Decimal("0.02355268736162796175043572472"),
                            "symbol": "AAPL",
                        },
                    ],
                    "quantity": Decimal("4"),
                    "sales": [],
                    "symbol": "AAPL",
                },
            },
            self.position_set.to_python(),
        )


class CopyTests(PositionSetTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.position_set.add_buy(
            "AAPL",
            datetime.date(2025, 3, 18),
            Decimal("4"),
            Decimal("212.29"),
        )
        self.position_set.add_sale(
            "AAPL",
            datetime.date(2025, 3, 19),
            Decimal("2"),
            Decimal("220.29"),
        )

    def test(self) -> None:
        self.assertEqual(
            self.position_set.to_python(), self.position_set.copy().to_python()
        )

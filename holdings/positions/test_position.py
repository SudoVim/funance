import datetime
from decimal import Decimal
from unittest import TestCase

from holdings.positions.position import Position


class PositionTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None
        self.position = Position("AAPL")


class AddBuyTests(PositionTestCase):
    def test(self) -> None:
        cmp_action = self.position.add_buy(
            datetime.date(2025, 3, 17),
            Decimal("4"),
            Decimal("213.49"),
        )
        assert cmp_action is not None
        self.assertEqual(
            {
                "action": "buy",
                "date": datetime.date(2025, 3, 17),
                "price": Decimal("213.49"),
                "quantity": Decimal("4"),
                "symbol": "AAPL",
                "total": Decimal("853.96"),
            },
            cmp_action.to_python(),
        )
        self.assertEqual(
            {
                "actions": [cmp_action.to_python()],
                "available_purchases": [cmp_action.to_python()],
                "cost_basis": Decimal("853.96"),
                "cost_basis_per_share": Decimal("213.49"),
                "generations": [],
                "quantity": Decimal("4"),
                "sales": [],
                "symbol": "AAPL",
            },
            self.position.to_python(),
        )

    def test_already_added(self) -> None:
        first_action = self.position.add_buy(
            datetime.date(2025, 3, 17),
            Decimal("4"),
            Decimal("213.49"),
        )
        assert first_action is not None
        cmp_action = self.position.add_buy(
            datetime.date(2025, 3, 17),
            Decimal("4"),
            Decimal("213.49"),
        )
        self.assertEqual(None, cmp_action)
        self.assertEqual(
            {
                "actions": [first_action.to_python()],
                "available_purchases": [first_action.to_python()],
                "cost_basis": Decimal("853.96"),
                "cost_basis_per_share": Decimal("213.49"),
                "generations": [],
                "quantity": Decimal("4"),
                "sales": [],
                "symbol": "AAPL",
            },
            self.position.to_python(),
        )


class AddSaleTests(PositionTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.buy_action = self.position.assert_add_buy(
            datetime.date(2025, 3, 17),
            Decimal("4"),
            Decimal("213.49"),
        )

    def test(self) -> None:
        cmp_action, cmp_sale_list = self.position.add_sale(
            datetime.date(2025, 3, 18),
            Decimal("2"),
            Decimal("220.49"),
        )
        assert cmp_action is not None
        self.assertEqual(
            {
                "action": "sell",
                "date": datetime.date(2025, 3, 18),
                "price": Decimal("220.49"),
                "quantity": Decimal("2"),
                "symbol": "AAPL",
                "total": Decimal("440.98"),
            },
            cmp_action.to_python(),
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
            {
                "actions": [
                    self.buy_action.to_python(),
                    cmp_action.to_python(),
                ],
                "available_purchases": [
                    {
                        "action": "buy",
                        "date": datetime.date(2025, 3, 17),
                        "price": Decimal("213.49"),
                        "quantity": Decimal("2"),
                        "symbol": "AAPL",
                        "total": Decimal("426.98"),
                    },
                ],
                "cost_basis": Decimal("426.98"),
                "cost_basis_per_share": Decimal("213.49"),
                "generations": [],
                "quantity": Decimal("2"),
                "sales": [
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
                "symbol": "AAPL",
            },
            self.position.to_python(),
        )

    def test_already_added(self) -> None:
        _ = self.position.assert_add_sale(
            datetime.date(2025, 3, 18),
            Decimal("2"),
            Decimal("220.49"),
        )
        cmp_action, cmp_sale_list = self.position.add_sale(
            datetime.date(2025, 3, 18),
            Decimal("2"),
            Decimal("220.49"),
        )
        self.assertEqual(None, cmp_action)
        self.assertEqual([], cmp_sale_list.to_python())


class AddGenerationTests(PositionTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.buy_action = self.position.assert_add_buy(
            datetime.date(2025, 3, 17),
            Decimal("4"),
            Decimal("213.49"),
        )

    def test(self) -> None:
        cmp_generation = self.position.add_generation(
            datetime.date(2025, 3, 17),
            "dividend",
            Decimal("24.19"),
        )
        assert cmp_generation is not None
        self.assertEqual(
            {
                "amount": Decimal("24.19"),
                "cost_basis": Decimal("853.96"),
                "date": datetime.date(2025, 3, 17),
                "generation_type": "dividend",
                "percent": Decimal("0.02832685371680172373413274626"),
                "symbol": "AAPL",
            },
            cmp_generation.to_python(),
        )
        self.assertEqual(
            [
                cmp_generation.to_python(),
            ],
            self.position.generations.to_python(),
        )

    def test_already_added(self) -> None:
        first_generation = self.position.add_generation(
            datetime.date(2025, 3, 17),
            "dividend",
            Decimal("24.19"),
        )
        assert first_generation is not None
        cmp_generation = self.position.add_generation(
            datetime.date(2025, 3, 17),
            "dividend",
            Decimal("24.19"),
        )
        self.assertEqual(None, cmp_generation)
        self.assertEqual(
            {
                "amount": Decimal("24.19"),
                "cost_basis": Decimal("853.96"),
                "date": datetime.date(2025, 3, 17),
                "generation_type": "dividend",
                "percent": Decimal("0.02832685371680172373413274626"),
                "symbol": "AAPL",
            },
            first_generation.to_python(),
        )
        self.assertEqual(
            [
                first_generation.to_python(),
            ],
            self.position.generations.to_python(),
        )


class AddSplitTests(PositionTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.buy_action = self.position.assert_add_buy(
            datetime.date(2025, 3, 17),
            Decimal("4"),
            Decimal("213.49"),
        )

    def test(self) -> None:
        self.position.add_split("AAPL2", Decimal("8"))
        self.assertEqual(
            {
                "actions": [
                    {
                        "action": "buy",
                        "date": datetime.date(2025, 3, 17),
                        "price": Decimal("106.745"),
                        "quantity": Decimal("8"),
                        "symbol": "AAPL2",
                        "total": Decimal("853.96"),
                    }
                ],
                "available_purchases": [
                    {
                        "action": "buy",
                        "date": datetime.date(2025, 3, 17),
                        "price": Decimal("106.745"),
                        "quantity": Decimal("8"),
                        "symbol": "AAPL2",
                        "total": Decimal("853.96"),
                    }
                ],
                "cost_basis": Decimal("853.96"),
                "cost_basis_per_share": Decimal("106.745"),
                "generations": [],
                "quantity": Decimal("8"),
                "sales": [],
                "symbol": "AAPL2",
            },
            self.position.to_python(),
        )


class AddDistributionTests(PositionTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.buy_action = self.position.assert_add_buy(
            datetime.date(2025, 3, 17),
            Decimal("4"),
            Decimal("213.49"),
        )

    def test(self) -> None:
        self.position.add_distribution(Decimal("4"))
        self.assertEqual(
            {
                "actions": [
                    {
                        "action": "buy",
                        "date": datetime.date(2025, 3, 17),
                        "price": Decimal("106.745"),
                        "quantity": Decimal("8"),
                        "symbol": "AAPL",
                        "total": Decimal("853.96"),
                    }
                ],
                "available_purchases": [
                    {
                        "action": "buy",
                        "date": datetime.date(2025, 3, 17),
                        "price": Decimal("106.745"),
                        "quantity": Decimal("8"),
                        "symbol": "AAPL",
                        "total": Decimal("853.96"),
                    }
                ],
                "cost_basis": Decimal("853.96"),
                "cost_basis_per_share": Decimal("106.745"),
                "generations": [],
                "quantity": Decimal("8"),
                "sales": [],
                "symbol": "AAPL",
            },
            self.position.to_python(),
        )


class CopyTests(PositionTestCase):
    def setUp(self) -> None:
        super().setUp()

        _ = self.position.assert_add_buy(
            datetime.date(2025, 3, 17),
            Decimal("4"),
            Decimal("213.49"),
        )
        _ = self.position.add_sale(
            datetime.date(2025, 3, 18),
            Decimal("2"),
            Decimal("220.49"),
        )

    def test(self) -> None:
        self.assertEqual(self.position.to_python(), self.position.copy().to_python())

import datetime
from decimal import Decimal
from unittest import TestCase

from holdings.positions.action import PositionAction


class PositionActionTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.action = PositionAction(
            "AAPL",
            datetime.date(2025, 3, 15),
            "buy",
            Decimal("3"),
            Decimal("234.56"),
        )


class CashOffsetTests(PositionActionTestCase):
    def test(self) -> None:
        self.assertEqual(
            {
                "action": "sell",
                "date": datetime.date(2025, 3, 15),
                "price": Decimal("1"),
                "quantity": Decimal("703.68"),
                "symbol": "CASH",
                "total": Decimal("703.68"),
            },
            self.action.cash_offset().to_python(),
        )


class AddSplitTests(PositionActionTestCase):
    def test_split(self) -> None:
        self.assertEqual(
            {
                "action": "buy",
                "date": datetime.date(2025, 3, 15),
                "price": Decimal("58.64"),
                "quantity": Decimal("12"),
                "symbol": "AAPL2",
                "total": Decimal("703.68"),
            },
            self.action.add_split(
                "AAPL2",
                Decimal("4"),
            ).to_python(),
        )

    def test_reverse_split(self) -> None:
        self.assertEqual(
            {
                "action": "buy",
                "date": datetime.date(2025, 3, 15),
                "price": Decimal("703.6800000000000000000000001"),
                "quantity": Decimal("0.9999999999999999999999999999"),
                "symbol": "AAPL2",
                "total": Decimal("703.68"),
            },
            self.action.add_split(
                "AAPL2",
                Decimal("1") / 3,
            ).to_python(),
        )


class PotentialProfitTests(PositionActionTestCase):
    def test_profit(self) -> None:
        self.assertEqual(
            Decimal("136.32"), self.action.potential_profit(Decimal("280.00"))
        )

    def test_loss(self) -> None:
        self.assertEqual(
            Decimal("-103.68"), self.action.potential_profit(Decimal("200.00"))
        )


class PotentialInterestTests(PositionActionTestCase):
    def test_positive(self) -> None:
        self.assertEqual(
            Decimal("0.1938571081500308359341419201"),
            self.action.potential_interest(
                self.action.date + datetime.timedelta(days=365),
                Decimal("280.00"),
            ),
        )

    def test_negative(self) -> None:
        self.assertEqual(
            Decimal("-0.1474406174662206357808966716"),
            self.action.potential_interest(
                self.action.date + datetime.timedelta(days=365),
                Decimal("200.00"),
            ),
        )


class TotalProfitTests(PositionActionTestCase):
    def test(self) -> None:
        self.assertEqual(
            Decimal("136.32"),
            PositionAction.total_profit(
                Decimal("280.00"),
                [
                    PositionAction(
                        "AAPL",
                        datetime.date(2025, 3, 15),
                        "buy",
                        Decimal("1"),
                        Decimal("234.56"),
                    ),
                    PositionAction(
                        "AAPL",
                        datetime.date(2025, 3, 15),
                        "buy",
                        Decimal("1"),
                        Decimal("234.56"),
                    ),
                    PositionAction(
                        "AAPL",
                        datetime.date(2025, 3, 15),
                        "buy",
                        Decimal("1"),
                        Decimal("234.56"),
                    ),
                ],
            ),
        )


class AveragePotentialInterestTests(PositionActionTestCase):
    def test(self) -> None:
        self.assertEqual(
            Decimal("0.1938571081500308359341419201"),
            PositionAction.average_potential_interest(
                self.action.date + datetime.timedelta(days=365),
                Decimal("280.00"),
                [
                    PositionAction(
                        "AAPL",
                        datetime.date(2025, 3, 15),
                        "buy",
                        Decimal("1"),
                        Decimal("234.56"),
                    ),
                    PositionAction(
                        "AAPL",
                        datetime.date(2025, 3, 15),
                        "buy",
                        Decimal("1"),
                        Decimal("234.56"),
                    ),
                    PositionAction(
                        "AAPL",
                        datetime.date(2025, 3, 15),
                        "buy",
                        Decimal("1"),
                        Decimal("234.56"),
                    ),
                ],
            ),
        )


class CopyTests(PositionActionTestCase):
    def test(self) -> None:
        self.assertEqual(
            {
                "action": "buy",
                "date": datetime.date(2025, 3, 15),
                "price": Decimal("234.56"),
                "quantity": Decimal("3"),
                "symbol": "AAPL",
                "total": Decimal("703.68"),
            },
            self.action.copy().to_python(),
        )


class ToPythonTests(PositionActionTestCase):
    def test(self) -> None:
        self.assertEqual(
            {
                "action": "buy",
                "date": datetime.date(2025, 3, 15),
                "price": Decimal("234.56"),
                "quantity": Decimal("3"),
                "symbol": "AAPL",
                "total": Decimal("703.68"),
            },
            self.action.to_python(),
        )


class KeyTests(PositionActionTestCase):
    def test(self) -> None:
        self.assertEqual(
            (
                datetime.date(2025, 3, 15),
                "buy",
                Decimal("3"),
                Decimal("234.56"),
            ),
            self.action.key(),
        )

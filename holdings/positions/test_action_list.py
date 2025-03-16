import datetime
from decimal import Decimal
from unittest import TestCase

from holdings.positions.action import PositionAction
from holdings.positions.action_list import ActionList


class ActionListTestCase(TestCase):
    def setUp(self) -> None:
        super().setUp()

        self.maxDiff = None
        self.action = PositionAction(
            "AAPL",
            datetime.date(2025, 3, 15),
            "buy",
            Decimal("3"),
            Decimal("234.56"),
        )
        self.list = ActionList([self.action])


class AddSplitTests(ActionListTestCase):
    def test(self) -> None:
        self.assertEqual(
            [
                {
                    "action": "buy",
                    "date": datetime.date(2025, 3, 15),
                    "price": Decimal("58.64"),
                    "quantity": Decimal("12"),
                    "symbol": "AAPL2",
                    "total": Decimal("703.68"),
                },
            ],
            self.list.add_split(
                "AAPL2",
                Decimal("4"),
            ).to_python(),
        )


class AppendTests(ActionListTestCase):
    def test_append(self) -> None:
        self.assertEqual(
            True,
            self.list.append(
                PositionAction(
                    "AAPL",
                    datetime.date(2025, 3, 16),
                    "buy",
                    Decimal("2"),
                    Decimal("220.56"),
                )
            ),
        )
        self.assertEqual(
            [
                {
                    "action": "buy",
                    "date": datetime.date(2025, 3, 15),
                    "price": Decimal("234.56"),
                    "quantity": Decimal("3"),
                    "symbol": "AAPL",
                    "total": Decimal("703.68"),
                },
                {
                    "action": "buy",
                    "date": datetime.date(2025, 3, 16),
                    "price": Decimal("220.56"),
                    "quantity": Decimal("2"),
                    "symbol": "AAPL",
                    "total": Decimal("441.12"),
                },
            ],
            self.list.to_python(),
        )

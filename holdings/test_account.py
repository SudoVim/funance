import datetime
from decimal import Decimal
from unittest.mock import MagicMock, call

from django_helpers.tests import DHTestCase
from holdings.account import (
    parse_positions,
    shore_up_buy_actions,
    sync_position_actions,
    sync_position_generations,
    sync_position_sales,
    sync_positions,
)
from holdings.factories import (
    HoldingAccountDocumentFactory,
    HoldingAccountFactory,
    HoldingAccountPositionFactory,
)
from holdings.models import HoldingAccountDocument
from holdings.positions.action import PositionAction
from holdings.positions.generation import PositionGeneration
from holdings.positions.position import Position
from holdings.positions.position_set import PositionSet
from holdings.positions.sale import PositionSale


class AccountTestCase(DHTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.set_module("holdings.account")


class ParsePositionsTests(AccountTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.holding_account = HoldingAccountFactory()

        self.positions = MagicMock(spec=PositionSet)
        self.StatementParser = self.patch_module("StatementParser", autospec=True)
        self.StatementParser.return_value.parse_positions.return_value = self.positions
        self.ActivityParser = self.patch_module("ActivityParser", autospec=True)
        self.ActivityParser.return_value.parse_positions.return_value = self.positions

        self.statement = HoldingAccountDocumentFactory(
            holding_account=self.holding_account,
            document_type=HoldingAccountDocument.DocumentType.STATEMENT,
        )
        self.activity = HoldingAccountDocumentFactory(
            holding_account=self.holding_account,
            document_type=HoldingAccountDocument.DocumentType.ACTIVITY,
        )

    def test(self) -> None:
        self.assertEqual(self.positions, parse_positions(self.holding_account))

        self.assertEqual(3, len(self.StatementParser.mock_calls))
        self.assertCalls(
            [
                call(self.statement),
                call().parse_positions(),
            ],
            self.StatementParser.mock_calls[:2],
        )
        self.assertCalls(
            [
                call(
                    self.activity,
                    account_number=self.holding_account.number,
                    aliases={},
                ),
                call().parse_positions(self.positions),
            ],
            self.ActivityParser,
        )


class SyncPositionsTests(AccountTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.holding_account = HoldingAccountFactory()
        self.positions = MagicMock(spec=PositionSet)
        self.position = MagicMock(spec=Position)
        self.position.symbol = "AAPL"
        self.position.quantity = Decimal("4")
        self.position.cost_basis = Decimal("123.45")
        self.positions.values.return_value = [self.position]

        self.sync_position_actions = self.patch_module(
            "sync_position_actions", autospec=True
        )
        self.sync_position_sales = self.patch_module(
            "sync_position_sales", autospec=True
        )
        self.shore_up_buy_actions = self.patch_module(
            "shore_up_buy_actions", autospec=True
        )
        self.sync_position_generations = self.patch_module(
            "sync_position_generations", autospec=True
        )

    def test(self) -> None:
        sync_positions(self.holding_account, self.positions)

        self.assertEqual(1, self.holding_account.positions.count())
        ha_position = self.holding_account.positions.get(ticker_symbol="AAPL")
        self.assertEqual("AAPL", ha_position.ticker_symbol)

        self.assertCalls(
            [
                call(ha_position, self.position),
            ],
            self.sync_position_actions,
        )
        self.assertCalls(
            [
                call(ha_position, self.position),
            ],
            self.sync_position_sales,
        )
        self.assertCalls(
            [
                call(ha_position),
            ],
            self.shore_up_buy_actions,
        )
        self.assertCalls(
            [
                call(ha_position, self.position),
            ],
            self.sync_position_generations,
        )

    def test_position_exists(self) -> None:
        ha_position = self.holding_account.positions.create(ticker_symbol="AAPL")

        sync_positions(self.holding_account, self.positions)

        self.assertEqual(1, self.holding_account.positions.count())

        self.assertCalls(
            [
                call(ha_position, self.position),
            ],
            self.sync_position_actions,
        )
        self.assertCalls(
            [
                call(ha_position, self.position),
            ],
            self.sync_position_sales,
        )
        self.assertCalls(
            [
                call(ha_position),
            ],
            self.shore_up_buy_actions,
        )
        self.assertCalls(
            [
                call(ha_position, self.position),
            ],
            self.sync_position_generations,
        )


class SyncPositionActionsTests(AccountTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.ha_position = HoldingAccountPositionFactory()
        self.position = MagicMock(spec=Position)
        self.action = PositionAction(
            "AAPL",
            datetime.date(2025, 3, 22),
            "buy",
            Decimal("4"),
            Decimal("218.27"),
        )
        self.position.actions = [self.action]

    def test(self) -> None:
        sync_position_actions(self.ha_position, self.position)

        self.assertEqual(1, self.ha_position.actions.count())
        ha_action = self.ha_position.actions.first()
        assert ha_action is not None

        self.assertAttrs(
            (
                datetime.date(2025, 3, 22),
                "buy",
                Decimal("4"),
                Decimal("4"),
                True,
                Decimal("218.27"),
            ),
            ha_action,
            "purchased_on",
            "action",
            "quantity",
            "remaining_quantity",
            "has_remaining_quantity",
            "price",
        )

    def test_sell(self) -> None:
        self.action.action = "sell"

        sync_position_actions(self.ha_position, self.position)

        self.assertEqual(1, self.ha_position.actions.count())
        ha_action = self.ha_position.actions.first()
        assert ha_action is not None

        self.assertAttrs(
            (
                datetime.date(2025, 3, 22),
                "sell",
                Decimal("4"),
                None,
                False,
                Decimal("218.27"),
            ),
            ha_action,
            "purchased_on",
            "action",
            "quantity",
            "remaining_quantity",
            "has_remaining_quantity",
            "price",
        )

    def test_already_added(self) -> None:
        self.ha_position.actions.create(
            purchased_on=datetime.date(2025, 3, 22),
            action="buy",
            quantity=Decimal("4"),
            remaining_quantity=Decimal("4"),
            has_remaining_quantity=True,
            price=Decimal("218.27"),
        )
        sync_position_actions(self.ha_position, self.position)

        self.assertEqual(1, self.ha_position.actions.count())
        ha_action = self.ha_position.actions.first()
        assert ha_action is not None

        self.assertAttrs(
            (
                datetime.date(2025, 3, 22),
                "buy",
                Decimal("4"),
                Decimal("4"),
                True,
                Decimal("218.27"),
            ),
            ha_action,
            "purchased_on",
            "action",
            "quantity",
            "remaining_quantity",
            "has_remaining_quantity",
            "price",
        )


class SyncPositionSalesTests(AccountTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.ha_position = HoldingAccountPositionFactory()
        self.position = MagicMock(spec=Position)
        self.sale = PositionSale(
            "AAPL",
            Decimal("4"),
            datetime.date(2024, 3, 22),
            Decimal("200.00"),
            datetime.date(2025, 3, 22),
            Decimal("218.27"),
        )
        self.position.sales = [self.sale]

    def test(self) -> None:
        sync_position_sales(self.ha_position, self.position)

        self.assertEqual(1, self.ha_position.sales.count())
        ha_sale = self.ha_position.sales.first()
        assert ha_sale is not None

        self.assertAttrs(
            (
                Decimal("4"),
                datetime.date(2024, 3, 22),
                Decimal("200.00"),
                datetime.date(2025, 3, 22),
                Decimal("218.27"),
            ),
            ha_sale,
            "quantity",
            "purchase_date",
            "purchase_price",
            "sale_date",
            "sale_price",
        )

    def test_already_added(self) -> None:
        self.ha_position.sales.create(
            quantity=Decimal("4"),
            purchase_date=datetime.date(2024, 3, 22),
            purchase_price=Decimal("200.00"),
            sale_date=datetime.date(2025, 3, 22),
            sale_price=Decimal("218.27"),
        )

        sync_position_sales(self.ha_position, self.position)

        self.assertEqual(1, self.ha_position.sales.count())
        ha_sale = self.ha_position.sales.first()
        assert ha_sale is not None

        self.assertAttrs(
            (
                Decimal("4"),
                datetime.date(2024, 3, 22),
                Decimal("200.00"),
                datetime.date(2025, 3, 22),
                Decimal("218.27"),
            ),
            ha_sale,
            "quantity",
            "purchase_date",
            "purchase_price",
            "sale_date",
            "sale_price",
        )


class ShoreUpBuyActionsTests(AccountTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.ha_position = HoldingAccountPositionFactory()
        self.position = MagicMock(spec=Position)
        self.ha_action = self.ha_position.actions.create(
            purchased_on=datetime.date(2024, 3, 22),
            action="buy",
            quantity=Decimal("4"),
            remaining_quantity=Decimal("4"),
            has_remaining_quantity=True,
            price=Decimal("218.27"),
        )
        self.ha_sales = self.ha_position.sales.create(
            quantity=Decimal("4"),
            purchase_date=datetime.date(2024, 3, 22),
            purchase_price=Decimal("200.00"),
            sale_date=datetime.date(2025, 3, 22),
            sale_price=Decimal("218.27"),
        )

    def test(self) -> None:
        shore_up_buy_actions(self.ha_position)

        self.ha_action.refresh_from_db()
        self.assertAttrs(
            (
                Decimal("0"),
                False,
            ),
            self.ha_action,
            "remaining_quantity",
            "has_remaining_quantity",
        )

    def test_partial(self) -> None:
        self.ha_sales.quantity = Decimal("2")
        self.ha_sales.save()

        shore_up_buy_actions(self.ha_position)

        self.ha_action.refresh_from_db()
        self.assertAttrs(
            (
                Decimal("2"),
                True,
            ),
            self.ha_action,
            "remaining_quantity",
            "has_remaining_quantity",
        )


class SyncPositionGenerationsTests(AccountTestCase):
    def setUp(self) -> None:
        super().setUp()

        self.ha_position = HoldingAccountPositionFactory()
        self.position = MagicMock(spec=Position)
        self.generation = PositionGeneration(
            "AAPL",
            datetime.date(2025, 3, 22),
            "dividend",
            Decimal("10.00"),
            Decimal("218.27"),
        )
        self.position.generations = [self.generation]

    def test(self) -> None:
        sync_position_generations(self.ha_position, self.position)

        self.assertEqual(1, self.ha_position.generations.count())
        ha_generation = self.ha_position.generations.first()
        assert ha_generation is not None

        self.assertAttrs(
            (
                datetime.date(2025, 3, 22),
                "dividend",
                Decimal("10"),
                Decimal("218.27"),
            ),
            ha_generation,
            "date",
            "event",
            "amount",
            "cost_basis",
        )

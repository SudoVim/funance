from decimal import Decimal

from django.test import TestCase

from accounts.models import Account
from funds.admin import FundVersionAdmin
from funds.funds import create_new_version
from funds.models import Fund, FundVersion, FundVersionAllocation
from funds.portfolio.admin import FundVersionInline
from funds.portfolio.models import Portfolio, PortfolioVersion
from funds.version_actions import apply_version_actions
from holdings.models import HoldingAccount, HoldingAccountPosition
from tickers.models import Ticker


class VersionActionTestCase(TestCase):
    """
    Shared fund whose portfolio share is worth $10.

    The fund owns 1,000 portfolio shares out of 10,000, so its budget is
    $10,000, and it has 1,000 internal shares. AAPL is a buy of 10 shares
    against a 60-share position priced at $100 (budget $2,000). MSFT floats
    with a 40-share position priced at $50.
    """

    def setUp(self) -> None:
        super().setUp()

        self.account = Account.objects.create(username="owner")
        self.portfolio = Portfolio.objects.create(
            owner=self.account,
            name="Main",
            shares=10000,
        )
        self.portfolio_version = PortfolioVersion.objects.create(
            portfolio=self.portfolio,
            shares=10000,
            start_cash=Decimal("0"),
            start_value=Decimal("100000"),
        )
        self.fund = Fund.objects.create(
            owner=self.account,
            name="Growth",
            portfolio=self.portfolio,
        )
        self.fund_version = FundVersion.objects.create(
            fund=self.fund,
            portfolio_version=self.portfolio_version,
            portfolio_shares=1000,
            shares=1000,
        )
        self.holding_account = HoldingAccount.objects.create(
            owner=self.account,
            portfolio=self.portfolio,
            name="Brokerage",
            number="1",
        )
        self.aapl = Ticker.objects.create(symbol="AAPL", current_price=Decimal("100"))
        self.msft = Ticker.objects.create(symbol="MSFT", current_price=Decimal("50"))
        HoldingAccountPosition.objects.create(
            holding_account=self.holding_account,
            ticker_symbol="AAPL",
            ticker=self.aapl,
            quantity=Decimal("60"),
        )
        HoldingAccountPosition.objects.create(
            holding_account=self.holding_account,
            ticker_symbol="MSFT",
            ticker=self.msft,
            quantity=Decimal("40"),
        )
        self.aapl_allocation = FundVersionAllocation.objects.create(
            version=self.fund_version,
            ticker=self.aapl,
            shares=200,
            version_action=FundVersionAllocation.VersionAction.BUY,
            modify_shares=10,
        )
        self.msft_allocation = FundVersionAllocation.objects.create(
            version=self.fund_version,
            ticker=self.msft,
            shares=800,
            version_action=FundVersionAllocation.VersionAction.FLOAT,
        )

    def shares_by_symbol(self) -> dict[str, int]:
        self.fund_version.refresh_from_db()
        return {
            allocation.ticker_id: allocation.shares
            for allocation in self.fund_version.allocations.all()
        }


class ApplyVersionActionsTests(VersionActionTestCase):
    def test_float_derives_portfolio_shares_from_allocation_buy(self) -> None:
        self.fund_version.modify_shares = 999
        self.fund_version.save(update_fields=["modify_shares"])

        apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(700, self.fund_version.portfolio_shares)
        self.assertEqual({"AAPL": 1000, "MSFT": 0}, self.shares_by_symbol())

    def test_float_derives_portfolio_shares_from_allocation_sell_remove(self) -> None:
        self.aapl_allocation.version_action = (
            FundVersionAllocation.VersionAction.SELL_REMOVE_SHARES
        )
        self.aapl_allocation.save(update_fields=["version_action"])

        apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(500, self.fund_version.portfolio_shares)
        self.assertEqual({"AAPL": 1000, "MSFT": 0}, self.shares_by_symbol())

    def test_float_sell_reallocate_keeps_portfolio_shares(self) -> None:
        self.aapl_allocation.version_action = (
            FundVersionAllocation.VersionAction.SELL_REALLOCATE_SHARES
        )
        self.aapl_allocation.save(update_fields=["version_action"])

        apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(1000, self.fund_version.portfolio_shares)
        self.assertEqual({"AAPL": 500, "MSFT": 500}, self.shares_by_symbol())

    def test_buy_adds_modify_shares_and_still_applies_allocations(self) -> None:
        self.fund_version.version_action = FundVersion.VersionAction.BUY
        self.fund_version.modify_shares = 50
        self.fund_version.save(update_fields=["version_action", "modify_shares"])

        apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(1050, self.fund_version.portfolio_shares)
        self.assertEqual({"AAPL": 667, "MSFT": 333}, self.shares_by_symbol())

    def test_buy_with_zero_modify_shares_still_applies_allocations(self) -> None:
        self.fund_version.version_action = FundVersion.VersionAction.BUY
        self.fund_version.modify_shares = 0
        self.fund_version.save(update_fields=["version_action", "modify_shares"])

        apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(1000, self.fund_version.portfolio_shares)
        self.assertEqual({"AAPL": 700, "MSFT": 300}, self.shares_by_symbol())

    def test_sell_remove_subtracts_modify_shares(self) -> None:
        self.fund_version.version_action = FundVersion.VersionAction.SELL_REMOVE_SHARES
        self.fund_version.modify_shares = 200
        self.fund_version.save(update_fields=["version_action", "modify_shares"])

        apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(800, self.fund_version.portfolio_shares)
        self.assertEqual({"AAPL": 875, "MSFT": 125}, self.shares_by_symbol())

    def test_sell_remove_clamps_at_zero_and_leaves_allocations(self) -> None:
        self.fund_version.version_action = FundVersion.VersionAction.SELL_REMOVE_SHARES
        self.fund_version.modify_shares = 250
        self.fund_version.portfolio_shares = 100
        self.fund_version.save(
            update_fields=["version_action", "modify_shares", "portfolio_shares"]
        )

        apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(0, self.fund_version.portfolio_shares)
        self.assertEqual({"AAPL": 200, "MSFT": 800}, self.shares_by_symbol())

    def test_hold_allocates_from_positions(self) -> None:
        self.fund_version.version_action = FundVersion.VersionAction.HOLD
        self.fund_version.modify_shares = 50
        self.fund_version.portfolio_version = None
        self.fund_version.save(
            update_fields=["version_action", "modify_shares", "portfolio_version"]
        )

        apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(1000, self.fund_version.portfolio_shares)
        self.assertEqual({"AAPL": 750, "MSFT": 250}, self.shares_by_symbol())

    def test_float_requires_portfolio_version(self) -> None:
        self.fund_version.portfolio_version = None
        self.fund_version.save(update_fields=["portfolio_version"])

        with self.assertRaisesMessage(
            AssertionError,
            "No portfolio version for fund version",
        ):
            apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(1000, self.fund_version.portfolio_shares)

    def test_buy_requires_portfolio_version(self) -> None:
        self.fund_version.version_action = FundVersion.VersionAction.BUY
        self.fund_version.modify_shares = 50
        self.fund_version.portfolio_version = None
        self.fund_version.save(
            update_fields=["version_action", "modify_shares", "portfolio_version"]
        )

        with self.assertRaisesMessage(
            AssertionError,
            "No portfolio version for fund version",
        ):
            apply_version_actions(self.fund_version)

        self.fund_version.refresh_from_db()
        self.assertEqual(1000, self.fund_version.portfolio_shares)
        self.assertEqual({"AAPL": 200, "MSFT": 800}, self.shares_by_symbol())


class CreateNewVersionTests(VersionActionTestCase):
    def test_copies_preselected_action(self) -> None:
        self.fund_version.version_action = FundVersion.VersionAction.SELL_REMOVE_SHARES
        self.fund_version.modify_shares = 42
        self.fund_version.save(update_fields=["version_action", "modify_shares"])

        new_version = create_new_version(self.fund_version)

        self.assertEqual(
            FundVersion.VersionAction.SELL_REMOVE_SHARES,
            new_version.version_action,
        )
        self.assertEqual(42, new_version.modify_shares)
        self.assertEqual(1000, new_version.portfolio_shares)
        copied = new_version.allocations.get(ticker=self.aapl)
        self.assertEqual(
            FundVersionAllocation.VersionAction.BUY,
            copied.version_action,
        )
        self.assertEqual(10, copied.modify_shares)


class VersionActionAdminTests(TestCase):
    def test_fields_are_editable_where_portfolio_shares_are_edited(self) -> None:
        self.assertIn("version_action", FundVersionAdmin.fields)
        self.assertIn("modify_shares", FundVersionAdmin.fields)
        self.assertNotIn("version_action", FundVersionAdmin.readonly_fields)
        self.assertNotIn("modify_shares", FundVersionAdmin.readonly_fields)

        self.assertIn("version_action", FundVersionInline.fields)
        self.assertIn("modify_shares", FundVersionInline.fields)
        self.assertNotIn("version_action", FundVersionInline.readonly_fields)
        self.assertNotIn("modify_shares", FundVersionInline.readonly_fields)

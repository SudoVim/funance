"""
Module related to fidelity-specific logic.
"""

import csv
import datetime
import re
from decimal import Decimal

import dateparser

from holdings.documents import DocumentParser
from holdings.models import HoldingAccountDocument
from holdings.positions.position import (
    AddBuyResponse,
    AddGenerationResponse,
    AddSaleResponse,
)
from holdings.positions.position_set import PositionSet
from holdings.positions.sale_list import SaleList


class StatementParser:
    """
    Parser for Fidelity account statements. This will effectively be used to
    create a single "buy" action for the current set of positions parsed.
    """

    document: HoldingAccountDocument
    parser: DocumentParser

    def __init__(self, document: HoldingAccountDocument) -> None:
        self.document = document
        self.parser = DocumentParser(self.document)

    def parse_positions(self) -> PositionSet:
        """
        Parse a set of initial positions out of the document.
        """
        file_str = self.document.document.name.split("/")[-1].split("-")[1]
        m = re.search(r"(\d+)", file_str)
        assert m is not None

        raw_date = m.groups()[0]
        statement_date = datetime.datetime.strptime(raw_date, "%m%d%Y").date()

        # Parse "normal" positions from the core account
        positions = PositionSet()
        _ = self.parse_actions_from_lines(
            positions,
            statement_date,
            self.parser.lines_between("Core Account", "Subtotal of")[1:],
        )

        # Parse mutual fund positions
        _ = self.parse_actions_from_lines(
            positions,
            statement_date,
            self.parser.lines_between("Mutual Funds", "Subtotal of")[1:],
        )

        return positions

    def parse_actions_from_lines(
        self,
        positions: PositionSet,
        statement_date: datetime.date,
        lines: list[str],
    ) -> list[AddBuyResponse]:
        """
        Parse a ``list`` of :class:`PositionAction` s from the given *lines*.
        """

        def iter_actions():
            for symbol, description, qty, price, _, _, cost_basis in csv.reader(lines):
                yield positions.add_buy(
                    symbol.strip() or description.strip(),
                    statement_date,
                    Decimal(qty),
                    (
                        Decimal(price)
                        if cost_basis == "not applicable"
                        else Decimal(cost_basis) / Decimal(qty)
                    ),
                )

        return list(iter_actions())


class ActivityParser:
    """
    Parser for Fidelity account activity. This will effectively be used to add
    position transactions on top of an existing timeline of transactions.
    """

    document: HoldingAccountDocument
    parser: DocumentParser
    account_number: str | None
    aliases: dict[str, str]

    def __init__(
        self,
        document: HoldingAccountDocument,
        account_number: str | None = None,
        aliases: dict[str, str] | None = None,
    ) -> None:
        self.document = document
        self.parser = DocumentParser(self.document)
        self.account_number = account_number
        self.aliases = aliases or {}

    def parse_positions(self, positions: PositionSet) -> PositionSet:
        """
        Parse a set of initial positions out of the document.
        """
        positions = positions.copy()
        lines = self.parser.lines_between("Run Date")

        def key(row: dict[str, str]) -> tuple[datetime.date, int]:
            parsed = dateparser.parse(row["Run Date"].strip())
            assert parsed is not None

            date = parsed.date()
            assert date is not None
            if row["Action"].strip().startswith("YOU BOUGHT"):
                return date, 0
            if row["Action"].strip().startswith("You bought"):
                return date, 0
            if row["Action"].strip().startswith("YOU SOLD"):
                return date, 1
            if row["Action"].strip().startswith("You sold"):
                return date, 1
            if row["Action"].strip().startswith("LONG-TERM CAP GAIN"):
                return date, 2

            # Last
            if row["Action"].strip().startswith("REINVESTMENT"):
                return date, 11
            return date, 10

        rows = sorted(list(csv.DictReader(lines)), key=key)
        for row in rows:
            self.parse_activity(positions, row)

        return positions

    def parse_activity(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Modify the given *positions* based on the parsed *row*.
        """
        if self.account_number is not None and "Account Number" in row:
            account_number = row["Account Number"].strip()
            if account_number != self.account_number:
                return

        action = row.get("Action")
        if action is None:
            return

        action = action.strip()
        if action.strip().startswith("REINVESTMENT CASH"):
            # There's always one of these paired with an "INTEREST EARNED"
            # activity. I can safely ignore it.
            return

        if action.startswith("INTEREST EARNED CASH"):
            _ = self.add_cash_interest(positions, row)
            return

        if action.startswith("LONG-TERM CAP GAIN"):
            _ = self.add_long_term_cap_gain(positions, row)
            return

        if action.startswith("SHORT-TERM CAP GAIN"):
            _ = self.add_short_term_cap_gain(positions, row)
            return

        if action.startswith("DIVIDEND RECEIVED"):
            _ = self.add_dividend(positions, row)
            return

        if action.startswith("DIVIDEND ADJUSTMENT"):
            _ = self.add_dividend(positions, row)
            return

        if action.startswith("MUNI TAXABLE INT"):
            _ = self.add_bond_interest(positions, row)
            return

        if action.startswith("INTEREST"):
            _ = self.add_bond_interest(positions, row)
            return

        if action.startswith("REINVESTMENT"):
            _ = self.add_reinvestment(positions, row)
            return

        if action.startswith("YOU BOUGHT"):
            _ = self.add_buy(positions, row)
            return

        if action.startswith("You bought"):
            _ = self.add_crypto_buy(positions, row)
            return

        if action.startswith("YOU SOLD"):
            _ = self.add_sale(positions, row)
            return

        if action.startswith("You sold"):
            _ = self.add_crypto_sale(positions, row)
            return

        if action.startswith("Electronic Funds Transfer Received"):
            _ = self.add_eft(positions, row)
            return

        if action.startswith("OTHER DEBIT transfer"):
            _ = self.add_debit_transfer(positions, row)
            return

        if action.startswith("OTHER CREDIT transfer"):
            _ = self.add_credit_transfer(positions, row)
            return

        if action.startswith("Transfer in from brokerage"):
            return

        if action.startswith("Transfer out to brokerage"):
            return

        # I don't have a way to interpret this, so let's just ignore it for
        # now. Reverse splits should be handled with the "TO" variant.
        if action.startswith("REVERSE SPLIT R/S TO"):
            return

        if action.startswith("REVERSE SPLIT R/S FROM"):
            _ = self.add_reverse_split(positions, row)
            return

        if action.startswith("MERGER MER FROM"):
            _ = self.add_merger_split(positions, row)
            return

        if action.startswith("IN LIEU OF FRX SHARE LEU PAYOUT"):
            _ = self.add_reverse_split_payout(positions, row)
            return

        if action.startswith("MERGER MER PAYOUT"):
            _ = self.add_merger_payout(positions, row)
            return

        if action.startswith("REDEMPTION PAYOUT"):
            _ = self.add_redemption_payout(positions, row)
            return

        if action.startswith("DISTRIBUTION"):
            _ = self.add_distribution(positions, row)
            return

        if action.startswith("ROYALTY TR PYMT"):
            _ = self.add_royalty_payment(positions, row)
            return

        if action.startswith("RETURN OF CAPITAL"):
            _ = self.add_return_of_capital(positions, row)
            return

        if action.startswith("FOREIGN TAX PAID"):
            _ = self.add_foreign_tax(positions, row)
            return

        if action.startswith("FEE CHARGED"):
            _ = self.add_fee(positions, row)
            return

        raise AssertionError(f"Unknown action: {action}")

    @staticmethod
    def parse_date(date_str: str) -> datetime.date:
        """
        Parse date from the given *date_str*.
        """
        dt = dateparser.parse(date_str.strip())
        assert dt is not None

        return dt.date()

    def apply_alias(self, symbol: str) -> str:
        """
        Apply any aliases to the given *symbol*.
        """
        return self.aliases.get(symbol, symbol)

    def add_cash_interest(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add cash interest generation denoted by the given *row*.
        """
        return positions.add_generation(
            "CASH",
            self.parse_date(row["Run Date"].strip()),
            "interest",
            Decimal(row["Amount"].strip()),
        )

    def add_long_term_cap_gain(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add long term capital gain generation from the given *row*.
        """
        return positions.add_generation(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            "long-term-cap-gain",
            Decimal(row["Amount"].strip()),
        )

    def add_short_term_cap_gain(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add short term capital gain generation from the given *row*.
        """
        return positions.add_generation(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            "short-term-cap-gain",
            Decimal(row["Amount"].strip()),
        )

    def add_dividend(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add dividend generation from the given *row*.
        """
        return positions.add_generation(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            "dividend",
            Decimal(row["Amount"].strip()),
        )

    def add_bond_interest(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add interest generation from the given *row*.
        """
        return positions.add_generation(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            "interest",
            Decimal(row["Amount"].strip()),
        )

    def add_reinvestment(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddBuyResponse:
        """
        Add reinvestment from a recent generation gain back into the position
        that generated it.
        """
        return positions.add_buy(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            Decimal(row["Quantity"].strip()),
            Decimal(row["Price"].strip()),
        )

    def add_buy(self, positions: PositionSet, row: dict[str, str]) -> AddBuyResponse:
        """
        Add a buy
        """
        action_toks = row["Action"].strip().split()
        price = Decimal(row["Price"].strip())
        quantity = Decimal(row["Quantity"].strip())

        # Bonds and CDs are priced out of $100
        if "BDS" in action_toks or "CD" in action_toks:
            quantity /= 100

        return positions.add_buy(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            quantity,
            price,
        )

    def add_crypto_buy(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddBuyResponse:
        """
        Add a buy
        """
        price = Decimal(row["Price ($)"].strip())
        quantity = Decimal(row["Quantity"].strip())

        return positions.add_buy(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            quantity,
            price,
        )

    def add_sale(self, positions: PositionSet, row: dict[str, str]) -> AddSaleResponse:
        """
        Add a sale
        """
        return positions.add_sale(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            Decimal(row["Quantity"].strip()) * -1,
            Decimal(row["Price ($)"].strip()),
        )

    def add_crypto_sale(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddSaleResponse:
        """
        Add a sale
        """
        return positions.add_sale(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            Decimal(row["Quantity"].strip()) * -1,
            Decimal(row["Price ($)"].strip()),
        )

    def add_eft(self, positions: PositionSet, row: dict[str, str]) -> AddBuyResponse:
        """
        Add an EFT
        """
        return None

    def add_debit_transfer(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddSaleResponse:
        """
        Add a transfer
        """
        return None, SaleList()

    def add_credit_transfer(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddBuyResponse:
        """
        Add a transfer
        """
        return None

    def add_reverse_split(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a reverse split.
        """
        symbol = self.apply_alias(row["Symbol"].strip())
        from_symbol = row["Action"].strip().split("#")[0].split()[-1]
        positions.add_split(from_symbol, symbol, Decimal(row["Quantity"].strip()))

    def add_merger_split(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a merger split.
        """
        symbol = self.apply_alias(row["Symbol"].strip())
        from_symbol = self.apply_alias(row["Action"].strip().split("#")[0].split()[-1])
        positions.add_split(from_symbol, symbol, Decimal(row["Quantity"].strip()))

    def add_reverse_split_payout(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddSaleResponse:
        """
        Add a reverse split payout (not enough shares to reverse split)
        """
        symbol = self.apply_alias(row["Symbol"].strip())
        if symbol not in positions:
            return None, SaleList()

        from_symbol = self.apply_alias(row["Action"].strip().split("#")[0].split()[-1])
        amount = Decimal(row["Amount"].strip()) * -1
        quantity = positions[from_symbol].quantity
        return positions.add_sale(
            from_symbol,
            self.parse_date(row["Run Date"].strip()),
            quantity,
            amount / quantity,
        )

    def add_merger_payout(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddSaleResponse:
        """
        Add a merger payout (ownership of company changed and opted to pay out
        its public investors)
        """
        # If there is no price, this payout was done in stock in a different
        # activity entry.
        price_raw = row["Price"].strip()
        if not price_raw:
            return None, SaleList()

        price = Decimal(price_raw)
        return positions.add_sale(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            Decimal(row["Quantity"].strip()) * -1,
            price,
        )

    def add_redemption_payout(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddSaleResponse:
        """
        Add a redemption payout (bond or CD has matured)
        """
        return positions.add_sale(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            Decimal(row["Quantity"].strip()) * -1,
            Decimal(row["Price"].strip()),
        )

    def add_distribution(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add a distribution
        """
        return positions.add_distribution(
            self.apply_alias(row["Symbol"].strip()), Decimal(row["Quantity"].strip())
        )

    def add_royalty_payment(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add a royalty payment
        """
        return positions.add_generation(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            "royalty-payment",
            Decimal(row["Amount"].strip()),
        )

    def add_return_of_capital(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add a return of capital
        """
        return positions.add_generation(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            "return-of-capital",
            Decimal(row["Amount"].strip()),
        )

    def add_foreign_tax(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add foreign tax payment
        """
        return positions.add_generation(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            "foreign-tax",
            Decimal(row["Amount"].strip()),
        )

    def add_fee(
        self, positions: PositionSet, row: dict[str, str]
    ) -> AddGenerationResponse:
        """
        Add a fee
        """
        return positions.add_generation(
            self.apply_alias(row["Symbol"].strip()),
            self.parse_date(row["Run Date"].strip()),
            "foreign-tax",
            Decimal(row["Amount"].strip()),
        )

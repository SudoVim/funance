"""
Module related to fidelity-specific logic.
"""

import dateparser
import csv
import datetime
from decimal import Decimal
import re
from holdings.documents import DocumentParser
from holdings.models import HoldingAccountDocument
from holdings.positions import PositionAction, PositionGeneration, PositionSet


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
        for action in self.parse_actions_from_lines(
            statement_date,
            self.parser.lines_between("Core Account", "Subtotal of")[1:],
        ):
            positions.add_action(action, offset_cash=False)

        # Parse mutual fund positions
        for action in self.parse_actions_from_lines(
            statement_date,
            self.parser.lines_between("Mutual Funds", "Subtotal of")[1:],
        ):
            positions.add_action(action, offset_cash=False)

        return positions

    def parse_actions_from_lines(
        self, statement_date: datetime.date, lines: list[str]
    ) -> list[PositionAction]:
        """
        Parse a ``list`` of :class:`PositionAction` s from the given *lines*.
        """
        ret = []
        for symbol, description, qty, price, _, _, cost_basis in csv.reader(lines):
            ret.append(
                PositionAction(
                    symbol.strip() or description.strip(),
                    statement_date,
                    "buy",
                    Decimal(qty),
                    (
                        Decimal(price)
                        if cost_basis == "not applicable"
                        else Decimal(cost_basis) / Decimal(qty)
                    ),
                )
            )

        return ret


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

        def key(row):
            date = dateparser.parse(row["Run Date"].strip()).date()
            assert date is not None
            if row["Action"].strip().startswith("YOU BOUGHT"):
                return date, 0
            if row["Action"].strip().startswith("YOU SOLD"):
                return date, 1
            if row["Action"].strip().startswith("LONG-TERM CAP GAIN"):
                return date, 2
            if row["Action"].strip().startswith("REINVESTMENT"):
                return date, 3
            return date, 2

        rows = sorted(list(csv.DictReader(lines)), key=key)
        for row in rows:
            self.parse_activity(positions, row)

        return positions

    def parse_activity(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Modify the given *positions* based on the parsed *row*.
        """
        if self.account_number is not None:
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
            self.add_cash_interest(positions, row)
            return

        if action.startswith("LONG-TERM CAP GAIN"):
            self.add_long_term_cap_gain(positions, row)
            return

        if action.startswith("SHORT-TERM CAP GAIN"):
            self.add_short_term_cap_gain(positions, row)
            return

        if action.startswith("DIVIDEND RECEIVED"):
            self.add_dividend(positions, row)
            return

        if action.startswith("DIVIDEND ADJUSTMENT"):
            self.add_dividend(positions, row)
            return

        if action.startswith("MUNI TAXABLE INT"):
            self.add_bond_interest(positions, row)
            return

        if action.startswith("INTEREST"):
            self.add_bond_interest(positions, row)
            return

        if action.startswith("REINVESTMENT"):
            self.add_reinvestment(positions, row)
            return

        if action.startswith("YOU BOUGHT"):
            self.add_buy(positions, row)
            return

        if action.startswith("YOU SOLD"):
            self.add_sale(positions, row)
            return

        if action.startswith("Electronic Funds Transfer Received"):
            self.add_eft(positions, row)
            return

        if action.startswith("OTHER DEBIT transfer"):
            self.add_debit_transfer(positions, row)
            return

        if action.startswith("OTHER CREDIT transfer"):
            self.add_credit_transfer(positions, row)
            return

        # I don't have a way to interpret this, so let's just ignore it for
        # now. Reverse splits should be handled with the "TO" variant.
        if action.startswith("REVERSE SPLIT R/S TO"):
            return

        if action.startswith("REVERSE SPLIT R/S FROM"):
            self.add_reverse_split(positions, row)
            return

        if action.startswith("MERGER MER FROM"):
            self.add_merger_split(positions, row)
            return

        if action.startswith("IN LIEU OF FRX SHARE LEU PAYOUT"):
            self.add_reverse_split_payout(positions, row)
            return

        if action.startswith("MERGER MER PAYOUT"):
            self.add_merger_payout(positions, row)
            return

        if action.startswith("REDEMPTION PAYOUT"):
            self.add_redemption_payout(positions, row)
            return

        if action.startswith("DISTRIBUTION"):
            self.add_distribution(positions, row)
            return

        if action.startswith("ROYALTY TR PYMT"):
            self.add_royalty_payment(positions, row)
            return

        if action.startswith("RETURN OF CAPITAL"):
            self.add_return_of_capital(positions, row)
            return

        if action.startswith("FOREIGN TAX PAID"):
            self.add_foreign_tax(positions, row)
            return

        if action.startswith("FEE CHARGED"):
            self.add_fee(positions, row)
            return

        import pdb

        pdb.set_trace()
        pass

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

    def add_cash_interest(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add cash interest generation denoted by the given *row*.
        """
        positions.add_generation(
            PositionGeneration(
                "CASH",
                self.parse_date(row["Run Date"].strip()),
                "interest",
                Decimal(row["Amount"].strip()),
            ),
            offset_cash=False,
        )

    def add_long_term_cap_gain(
        self, positions: PositionSet, row: dict[str, str]
    ) -> None:
        """
        Add long term capital gain generation from the given *row*.
        """
        positions.add_generation(
            PositionGeneration(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "long-term-cap-gain",
                Decimal(row["Amount"].strip()),
            ),
        )

    def add_short_term_cap_gain(
        self, positions: PositionSet, row: dict[str, str]
    ) -> None:
        """
        Add short term capital gain generation from the given *row*.
        """
        positions.add_generation(
            PositionGeneration(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "short-term-cap-gain",
                Decimal(row["Amount"].strip()),
            ),
        )

    def add_dividend(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add dividend generation from the given *row*.
        """
        positions.add_generation(
            PositionGeneration(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "dividend",
                Decimal(row["Amount"].strip()),
            ),
        )

    def add_bond_interest(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add interest generation from the given *row*.
        """
        positions.add_generation(
            PositionGeneration(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "interest",
                Decimal(row["Amount"].strip()),
            ),
        )

    def add_reinvestment(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add reinvestment from a recent generation gain back into the position
        that generated it.
        """
        positions.add_action(
            PositionAction(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "buy",
                Decimal(row["Quantity"].strip()),
                Decimal(row["Price"].strip()),
            ),
        )

    def add_buy(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a buy
        """
        action_toks = row["Action"].strip().split()
        price = Decimal(row["Quantity"].strip())
        quantity = Decimal(row["Price"].strip())

        # Bonds and CDs are priced out of $100
        if "BDS" in action_toks or "CD" in action_toks:
            quantity /= 100

        positions.add_action(
            PositionAction(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "buy",
                price,
                quantity,
            ),
        )

    def add_sale(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a sale
        """
        positions.add_action(
            PositionAction(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "sell",
                Decimal(row["Quantity"].strip()) * -1,
                Decimal(row["Price"].strip()),
            ),
        )

    def add_eft(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add an EFT
        """
        positions.add_action(
            PositionAction(
                "CASH",
                self.parse_date(row["Run Date"].strip()),
                "buy",
                Decimal(row["Amount"].strip()),
                Decimal("1"),
            ),
            offset_cash=False,
        )

    def add_debit_transfer(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a transfer
        """
        positions.add_action(
            PositionAction(
                "CASH",
                self.parse_date(row["Run Date"].strip()),
                "sell",
                Decimal(row["Amount"].strip()) * -1,
                Decimal("1"),
            ),
            offset_cash=False,
        )

    def add_credit_transfer(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a transfer
        """
        positions.add_action(
            PositionAction(
                "CASH",
                self.parse_date(row["Run Date"].strip()),
                "buy",
                Decimal(row["Amount"].strip()) * -1,
                Decimal("1"),
            ),
            offset_cash=False,
        )

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
        from_symbol = row["Action"].strip().split("#")[0].split()[-1]
        positions.add_split(from_symbol, symbol, Decimal(row["Quantity"].strip()))

    def add_reverse_split_payout(
        self, positions: PositionSet, row: dict[str, str]
    ) -> None:
        """
        Add a reverse split payout (not enough shares to reverse split)
        """
        symbol = self.apply_alias(row["Symbol"].strip())
        if symbol not in positions.positions.keys():
            return

        from_symbol = row["Action"].strip().split("#")[0].split()[-1]
        amount = Decimal(row["Amount"].strip()) * -1
        quantity = positions.positions[from_symbol].quantity
        positions.add_action(
            PositionAction(
                from_symbol,
                self.parse_date(row["Run Date"].strip()),
                "sell",
                quantity,
                amount / quantity,
            ),
        )

    def add_merger_payout(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a merger payout (ownership of company changed and opted to pay out
        its public investors)
        """
        symbol = self.apply_alias(row["Symbol"].strip())
        if symbol not in positions.positions.keys():
            return

        positions.add_action(
            PositionAction(
                symbol,
                self.parse_date(row["Run Date"].strip()),
                "sell",
                Decimal(row["Quantity"].strip()) * -1,
                Decimal(row["Price"].strip()),
            ),
        )

    def add_redemption_payout(
        self, positions: PositionSet, row: dict[str, str]
    ) -> None:
        """
        Add a redemption payout (bond or CD has matured)
        """
        symbol = self.apply_alias(row["Symbol"].strip())
        if symbol not in positions.positions.keys():
            return

        positions.add_action(
            PositionAction(
                symbol,
                self.parse_date(row["Run Date"].strip()),
                "sell",
                Decimal(row["Quantity"].strip()) * -1,
                Decimal(row["Price"].strip()),
            ),
        )

    def add_distribution(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a distribution
        """
        symbol = row["Symbol"].strip()
        positions.add_distribution(symbol, Decimal(row["Quantity"].strip()))

    def add_royalty_payment(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a royalty payment
        """
        positions.add_generation(
            PositionGeneration(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "royalty-payment",
                Decimal(row["Amount"].strip()),
            ),
        )

    def add_return_of_capital(
        self, positions: PositionSet, row: dict[str, str]
    ) -> None:
        """
        Add a return of capital
        """
        positions.add_generation(
            PositionGeneration(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "return-of-capital",
                Decimal(row["Amount"].strip()),
            ),
        )

    def add_foreign_tax(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add foreign tax payment
        """
        positions.add_generation(
            PositionGeneration(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "foreign-tax",
                Decimal(row["Amount"].strip()),
            ),
        )

    def add_fee(self, positions: PositionSet, row: dict[str, str]) -> None:
        """
        Add a fee
        """
        positions.add_generation(
            PositionGeneration(
                self.apply_alias(row["Symbol"].strip()),
                self.parse_date(row["Run Date"].strip()),
                "foreign-tax",
                Decimal(row["Amount"].strip()),
            ),
        )

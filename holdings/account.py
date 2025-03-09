from holdings.fidelity import ActivityParser, StatementParser
from holdings.models import (
    HoldingAccount,
    HoldingAccountDocument,
    HoldingAccountPosition,
)
from holdings.positions import Position, PositionSet


def parse_positions(self: HoldingAccount) -> PositionSet:
    """
    Parse the positions from the given :class:`HoldingAccount` into a
    :class:`PositionSet`.
    """
    statement = (
        self.documents.filter(
            document_type=HoldingAccountDocument.DocumentType.STATEMENT,
        )
        .order_by("-created_at")
        .first()
    )
    assert statement is not None

    positions = StatementParser(statement).parse_positions()

    aliases = self.aliases_dict
    activities = self.documents.filter(
        document_type=HoldingAccountDocument.DocumentType.ACTIVITY,
        created_at__gt=statement.created_at,
    ).order_by("order", "created_at")
    for activity in activities:
        parser = ActivityParser(activity, account_number=self.number, aliases=aliases)
        positions = parser.parse_positions(positions)

    return positions


def sync_actions(self: HoldingAccount, positions: PositionSet) -> None:
    """
    Sync actions for the given *positions*.
    """
    for position in positions.positions.values():
        ha_position, _ = self.positions.get_or_create(ticker_symbol=position.symbol)
        sync_position_actions(ha_position, position)


def sync_position_actions(self: HoldingAccountPosition, position: Position) -> None:
    """
    Sync actions for the given *positions* for the given *symbol*.
    """
    for action in position.actions:
        _ = self.actions.get_or_create(
            purchased_on=action.date,
            action=action.action,
            quantity=action.quantity,
            price=action.price,
        )

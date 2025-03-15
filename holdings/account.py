from decimal import Decimal

from holdings.fidelity import ActivityParser, StatementParser
from holdings.models import (
    HoldingAccount,
    HoldingAccountAction,
    HoldingAccountDocument,
    HoldingAccountGeneration,
    HoldingAccountPosition,
    HoldingAccountSale,
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


def sync_positions(self: HoldingAccount, positions: PositionSet) -> None:
    """
    Sync actions for the given *positions*.
    """
    for position in positions.positions.values():
        ha_position, _ = self.positions.get_or_create(ticker_symbol=position.symbol)
        sync_position_actions(ha_position, position)
        sync_position_sales(ha_position, position)
        sync_position_generations(ha_position, position)


def sync_position_actions(self: HoldingAccountPosition, position: Position) -> None:
    """
    Sync actions for the given *positions* for the given *symbol*.
    """

    def get_actions_insert():
        latest_action = self.actions.order_by("-purchased_on").first()
        for action in position.actions:
            if latest_action and action.date <= latest_action.purchased_on:
                continue

            yield HoldingAccountAction(
                position=self,
                purchased_on=action.date,
                action=action.action,
                quantity=action.quantity,
                price=action.price.quantize(Decimal("0.00000001")),
            )

    _ = self.actions.bulk_create(get_actions_insert())


def sync_position_sales(self: HoldingAccountPosition, position: Position) -> None:
    """
    Sync sales for the given *positions* for the given *symbol*.
    """

    def get_sales_insert():
        latest_sale = self.sales.order_by("-sale_date").first()
        for sale in position.sales:
            if latest_sale and sale.sale_date <= latest_sale.sale_date:
                continue

            yield HoldingAccountSale(
                position=self,
                quantity=sale.quantity,
                purchase_date=sale.purchase_date,
                purchase_price=sale.purchase_price.quantize(Decimal("0.00000001")),
                sale_date=sale.sale_date,
                sale_price=sale.sale_price.quantize(Decimal("0.00000001")),
            )

    _ = self.sales.bulk_create(get_sales_insert())


def sync_position_generations(self: HoldingAccountPosition, position: Position) -> None:
    """
    Sync generations for the given *positions* for the given *symbol*.
    """

    def get_generations_insert():
        latest_generation = self.generations.order_by("-date").first()
        for generation in position.generations:
            if latest_generation and generation.date <= latest_generation.date:
                continue

            yield HoldingAccountGeneration(
                position=self,
                date=generation.date,
                event=generation.generation_type,
                amount=generation.amount,
                cost_basis=generation.cost_basis,
            )

    _ = self.generations.bulk_create(get_generations_insert())

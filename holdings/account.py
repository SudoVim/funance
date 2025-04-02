from decimal import Decimal
from typing import cast

from django_rq import job

from holdings.fidelity import ActivityParser, StatementParser
from holdings.models import (
    HoldingAccount,
    HoldingAccountAction,
    HoldingAccountDocument,
    HoldingAccountGeneration,
    HoldingAccountPosition,
    HoldingAccountSale,
)
from holdings.positions.position import Position
from holdings.positions.position_set import PositionSet


@job("low")
def parse_and_sync_positions(self: HoldingAccount) -> None:
    """
    Parse positions and then sync them to the database.
    """
    positions = parse_positions(self)
    sync_positions(self, positions)


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
    positions = PositionSet()
    if statement is not None:
        positions = StatementParser(statement).parse_positions()

    aliases = self.aliases_dict
    activities = self.documents.filter(
        document_type=HoldingAccountDocument.DocumentType.ACTIVITY,
    ).order_by("order", "created_at")
    for activity in activities:
        parser = ActivityParser(activity, account_number=self.number, aliases=aliases)
        positions = parser.parse_positions(positions)

    return positions


def sync_positions(self: HoldingAccount, positions: PositionSet) -> None:
    """
    Sync actions for the given *positions*.
    """
    for position in positions.values():
        ha_position, _ = self.positions.get_or_create(ticker_symbol=position.symbol)
        sync_position_actions(ha_position, position)
        sync_position_sales(ha_position, position)
        shore_up_buy_actions(ha_position)
        sync_position_generations(ha_position, position)

        ha_position.quantity = position.quantity
        ha_position.cost_basis = position.cost_basis
        ha_position.save()


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
                remaining_quantity=(
                    action.quantity
                    if action.action == HoldingAccountAction.Action.BUY
                    else None
                ),
                has_remaining_quantity=(
                    True if action.action == HoldingAccountAction.Action.BUY else False
                ),
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


def shore_up_buy_actions(self: HoldingAccountPosition) -> None:
    """
    Shore up buy actions by marking up the remaining quantity
    """

    def get_spent_buys():
        remaining_sales = Decimal(sum(s.quantity for s in self.sales.iterator()))
        for action in self.actions.order_by("purchased_on").iterator():
            if action.action != HoldingAccountAction.Action.BUY:
                action.remaining_quantity = None
                action.has_remaining_quantity = False
                yield action
                continue

            if remaining_sales <= 0:
                action.remaining_quantity = action.quantity
                action.has_remaining_quantity = True
                yield action
                continue

            remaining_sales -= action.quantity
            if remaining_sales > 0:
                action.remaining_quantity = Decimal("0")
                action.has_remaining_quantity = False
                yield action
                continue

            action.remaining_quantity = -remaining_sales
            action.has_remaining_quantity = cast(Decimal, action.remaining_quantity) > 0
            yield action

    _ = self.actions.bulk_update(
        get_spent_buys(),
        fields=[
            "remaining_quantity",
            "has_remaining_quantity",
        ],
    )


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

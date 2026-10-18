from decimal import Decimal

from django.db import transaction

from funds.models import FundVersion, FundVersionAllocation


def apply_version_actions(fund_version: FundVersion) -> None:
    """
    Apply all version actions for the given *fund_version*.
    """
    with transaction.atomic():
        _apply_version_actions(fund_version)


def _apply_version_actions(fund_version: FundVersion) -> None:
    portfolio_version = fund_version.portfolio_version
    if portfolio_version is None:
        raise AssertionError("No portfolio version for fund version")

    # First, figure out the portfolio share delta for the FundVersion itself.
    value_delta = Decimal("0")
    for allocation in fund_version.allocations.all():
        share_delta = Decimal("0")
        match allocation.version_action:
            case FundVersionAllocation.VersionAction.SELL_REMOVE_SHARES:
                share_delta = allocation.budget_delta_shares - allocation.modify_shares
            case FundVersionAllocation.VersionAction.BUY:
                share_delta = allocation.budget_delta_shares + allocation.modify_shares
            case _:
                continue

        value_delta += allocation.ticker.current_price * share_delta

    # Figure out how much the portfolio shares should be modified by
    portfolio_share_value = (
        portfolio_version.start_budget / portfolio_version.current_shares
    )
    if portfolio_share_value is None:
        raise AssertionError("Portfolio share value is $0")

    portfolio_share_delta = value_delta / portfolio_share_value
    fund_version.portfolio_shares += int(
        Decimal(portfolio_share_delta).quantize(Decimal("1"))
    )
    fund_version.save(update_fields=["portfolio_shares", "updated_at"])

    fund_share_value = fund_version.budget / fund_version.shares
    if fund_share_value is None:
        raise AssertionError("Share value is $0")

    # Next, we can figure out which positions need their shares adjusted
    # because of an explicit hold, sell, buy operation.
    for allocation in fund_version.allocations.all():
        share_delta = 0
        match allocation.version_action:
            case FundVersionAllocation.VersionAction.HOLD:
                share_delta = 0
            case FundVersionAllocation.VersionAction.SELL_REALLOCATE_SHARES:
                share_delta = -allocation.modify_shares
            case FundVersionAllocation.VersionAction.SELL_REMOVE_SHARES:
                share_delta = -allocation.modify_shares
            case FundVersionAllocation.VersionAction.BUY:
                share_delta = allocation.modify_shares
            case _:
                continue

        new_value = (
            Decimal(allocation.position_shares + share_delta)
            * allocation.ticker.current_price
        )
        allocation.shares = int(
            Decimal(new_value / fund_version.budget * fund_version.shares).quantize(
                Decimal("1")
            )
        )
        allocation.save(update_fields=["shares", "updated_at"])

    allocated_shares = allocated_shares = sum(
        a.shares for a in fund_version.allocations.all()
    )
    remaining_shares = fund_version.shares - allocated_shares

    float_shares = sum(
        a.shares
        for a in fund_version.allocations.all()
        if a.version_action == FundVersionAllocation.VersionAction.FLOAT
    )
    if float_shares == 0:
        return

    # Finally, re-allocate remaining shares to all "float" positions
    for allocation in fund_version.allocations.all():
        if allocation.version_action != FundVersionAllocation.VersionAction.FLOAT:
            continue

        fund_version_share_delta = (
            Decimal(allocation.shares) / float_shares * remaining_shares
        )
        allocation.shares += int(
            Decimal(fund_version_share_delta).quantize(Decimal("1"))
        )
        allocation.save(update_fields=["shares", "updated_at"])

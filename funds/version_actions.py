from decimal import Decimal

from django.db import transaction

from funds.funds import allocate_from_position
from funds.models import FundVersion, FundVersionAllocation


def apply_version_actions(fund_version: FundVersion) -> None:
    """
    Apply preselected actions for the given *fund_version* and its allocations.

    ``version_action`` on the fund version chooses the portfolio-share change:

    - ``FLOAT`` derives that change from allocation actions.
    - ``HOLD`` leaves portfolio shares unchanged and allocates this version's
      shares from the positions already held.
    - ``BUY`` and ``SELL_REMOVE_SHARES`` add or remove ``modify_shares``
      portfolio shares. That count replaces the portfolio-share change
      allocation actions would otherwise imply. Allocation actions still
      update each allocation's share target.
    """
    with transaction.atomic():
        _apply_version_actions(fund_version)


def _apply_version_actions(fund_version: FundVersion) -> None:
    match fund_version.version_action:
        case FundVersion.VersionAction.HOLD:
            # Hold steady: rebase fund shares on current positions instead of
            # buying, selling, or changing how many portfolio shares the fund
            # owns. Allocation actions are not applied.
            allocate_from_position(fund_version)
        case FundVersion.VersionAction.BUY:
            _apply_explicit_portfolio_share_change(
                fund_version,
                fund_version.modify_shares,
            )
        case FundVersion.VersionAction.SELL_REMOVE_SHARES:
            _apply_explicit_portfolio_share_change(
                fund_version,
                -fund_version.modify_shares,
            )
        case _:
            _apply_derived_portfolio_share_change(fund_version)
            _apply_allocation_actions(fund_version)


def _apply_explicit_portfolio_share_change(
    fund_version: FundVersion,
    delta: int,
) -> None:
    """
    Change portfolio shares by *delta*, then apply allocation actions.

    Allocation actions no longer move portfolio shares when the fund version
    action is explicit. Their share targets are still updated, unless the
    resulting fund budget is ``$0`` and those targets are undefined.
    """
    if fund_version.portfolio_version is None:
        raise AssertionError("No portfolio version for fund version")

    _set_portfolio_shares(
        fund_version,
        max(0, fund_version.portfolio_shares + delta),
    )
    if fund_version.budget == 0:
        return

    _apply_allocation_actions(fund_version)


def _set_portfolio_shares(fund_version: FundVersion, portfolio_shares: int) -> None:
    fund_version.portfolio_shares = portfolio_shares
    fund_version.save(update_fields=["portfolio_shares", "updated_at"])


def _apply_derived_portfolio_share_change(fund_version: FundVersion) -> None:
    """
    Change portfolio shares from allocation buy and sell-remove actions.
    """
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


def _apply_allocation_actions(fund_version: FundVersion) -> None:
    """
    Update allocation share targets from each allocation's preselected action.
    """
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

    allocated_shares = sum(a.shares for a in fund_version.allocations.all())
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

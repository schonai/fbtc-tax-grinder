from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from fbtc_taxgrinder.models import (
    Disposition, Lot, LotState, MonthProceeds, MonthResult,
)


@dataclass
class PeriodResult:
    total_btc_sold: Decimal
    cost_basis_of_sold: Decimal
    total_expense: Decimal
    gain_loss: Decimal
    adj_btc: Decimal
    adj_basis: Decimal


def compute_period(
    *,
    days_held: Decimal,
    days_in_month: Decimal,
    shares: Decimal,
    adj_btc: Decimal,
    adj_basis: Decimal,
    original_total_cost: Decimal,
    monthly_btc_sold_per_share: Decimal,
    monthly_proceeds_per_share_usd: Decimal,
) -> PeriodResult:
    """Run Steps 1-6 for a single contiguous period within a month."""
    if days_held == 0 or shares == 0:
        return PeriodResult(
            total_btc_sold=Decimal("0"),
            cost_basis_of_sold=Decimal("0"),
            total_expense=Decimal("0"),
            gain_loss=Decimal("0"),
            adj_btc=adj_btc,
            adj_basis=adj_basis,
        )

    proration = days_held / days_in_month

    # Step 2
    total_btc_sold = Decimal("0")
    cost_basis_of_sold = Decimal("0")
    if monthly_btc_sold_per_share != 0:
        btc_sold_per_share = proration * monthly_btc_sold_per_share
        total_btc_sold = btc_sold_per_share * shares
        # Step 3
        cost_basis_of_sold = (total_btc_sold / adj_btc) * original_total_cost

    # Step 4
    expense_per_share = proration * monthly_proceeds_per_share_usd
    total_expense = expense_per_share * shares

    # Step 5
    gain_loss = total_expense - cost_basis_of_sold

    # Step 6
    new_adj_btc = adj_btc - total_btc_sold
    new_adj_basis = adj_basis - cost_basis_of_sold

    return PeriodResult(
        total_btc_sold=total_btc_sold,
        cost_basis_of_sold=cost_basis_of_sold,
        total_expense=total_expense,
        gain_loss=gain_loss,
        adj_btc=new_adj_btc,
        adj_basis=new_adj_basis,
    )


@dataclass
class LotMonthInput:
    lot: Lot
    year: int
    month: int
    adj_btc: Decimal
    adj_basis: Decimal
    shares: Decimal
    month_proceeds: MonthProceeds


@dataclass
class LotMonthOutput:
    month_result: MonthResult
    dispositions: list[Disposition]
    new_state: LotState


def _month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def _month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def compute_lot_month(inp: LotMonthInput) -> LotMonthOutput | None:
    """Compute one month for one lot, handling mid-month sells."""
    month_end = _month_end(inp.year, inp.month)
    month_start_date = _month_start(inp.year, inp.month)
    days_in_month = Decimal(str(calendar.monthrange(inp.year, inp.month)[1]))

    # Check if lot is active this month
    if inp.lot.purchase_date > month_end:
        return None

    # Determine base days_held for the full month
    if inp.lot.purchase_date >= month_start_date:
        # First month: prorate from purchase date
        full_days_held = Decimal(str((month_end - inp.lot.purchase_date).days))
        if full_days_held == 0:
            return None  # Purchased on last day, starts next month
        period_start = inp.lot.purchase_date
    else:
        full_days_held = days_in_month
        period_start = month_start_date

    # Find sell events in this month for this lot
    sell_events = [
        e for e in inp.lot.events
        if e.type == "sell"
        and e.date.year == inp.year
        and e.date.month == inp.month
    ]
    sell_events.sort(key=lambda e: e.date)

    adj_btc = inp.adj_btc
    adj_basis = inp.adj_basis
    shares = inp.shares
    total_btc_sold = Decimal("0")
    total_cost_basis = Decimal("0")
    total_expense = Decimal("0")
    total_gain_loss = Decimal("0")
    dispositions: list[Disposition] = []

    if not sell_events:
        # Simple case: no sells, run full period
        pr = compute_period(
            days_held=full_days_held,
            days_in_month=days_in_month,
            shares=shares,
            adj_btc=adj_btc,
            adj_basis=adj_basis,
            original_total_cost=inp.lot.total_cost,
            monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
            monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
        )
        return LotMonthOutput(
            month_result=MonthResult(
                month=inp.month,
                days_held=full_days_held,
                days_in_month=days_in_month,
                shares=shares,
                total_btc_sold=pr.total_btc_sold,
                cost_basis_of_sold=pr.cost_basis_of_sold,
                total_expense=pr.total_expense,
                gain_loss=pr.gain_loss,
                adj_btc=pr.adj_btc,
                adj_basis=pr.adj_basis,
            ),
            dispositions=[],
            new_state=LotState(adj_btc=pr.adj_btc, adj_basis=pr.adj_basis, shares=shares),
        )

    # Complex case: sells split the month into phases
    current_start = period_start

    for event in sell_events:
        # Phase 1: Pre-sell expense computation
        pre_days = Decimal(str((event.date - current_start).days))
        if pre_days > 0:
            pr = compute_period(
                days_held=pre_days,
                days_in_month=days_in_month,
                shares=shares,
                adj_btc=adj_btc,
                adj_basis=adj_basis,
                original_total_cost=inp.lot.total_cost,
                monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
                monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
            )
            total_btc_sold += pr.total_btc_sold
            total_cost_basis += pr.cost_basis_of_sold
            total_expense += pr.total_expense
            total_gain_loss += pr.gain_loss
            adj_btc = pr.adj_btc
            adj_basis = pr.adj_basis

        # Phase 2: Disposition
        disposed_btc = adj_btc * (event.shares / shares)
        disposed_basis = adj_basis * (event.shares / shares)
        disposition_gain_loss = event.proceeds - disposed_basis

        dispositions.append(Disposition(
            lot_id=inp.lot.id,
            disposition_id=event.disposition_id,
            date_sold=event.date,
            shares_sold=event.shares,
            proceeds=event.proceeds,
            disposed_btc=disposed_btc,
            disposed_basis=disposed_basis,
            gain_loss=disposition_gain_loss,
        ))

        adj_btc -= disposed_btc
        adj_basis -= disposed_basis
        shares -= event.shares
        current_start = event.date

    # Phase 3: Post-sell expense computation (if shares remain)
    if shares > 0:
        post_days = Decimal(str((month_end - current_start).days))
        if post_days > 0:
            pr = compute_period(
                days_held=post_days,
                days_in_month=days_in_month,
                shares=shares,
                adj_btc=adj_btc,
                adj_basis=adj_basis,
                original_total_cost=inp.lot.total_cost,
                monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
                monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
            )
            total_btc_sold += pr.total_btc_sold
            total_cost_basis += pr.cost_basis_of_sold
            total_expense += pr.total_expense
            total_gain_loss += pr.gain_loss
            adj_btc = pr.adj_btc
            adj_basis = pr.adj_basis

    return LotMonthOutput(
        month_result=MonthResult(
            month=inp.month,
            days_held=full_days_held,  # Total days lot was active in month
            days_in_month=days_in_month,
            shares=inp.shares,  # Starting shares for the month
            total_btc_sold=total_btc_sold,
            cost_basis_of_sold=total_cost_basis,
            total_expense=total_expense,
            gain_loss=total_gain_loss,
            adj_btc=adj_btc,
            adj_basis=adj_basis,
        ),
        dispositions=dispositions,
        new_state=LotState(adj_btc=adj_btc, adj_basis=adj_basis, shares=shares),
    )

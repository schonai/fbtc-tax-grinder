"""WHFIT 6-step gain/loss computation engine for FBTC tax lots."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import Enum

from fbtc_taxgrinder.models import (
    Disposition,
    HoldingTerm,
    Lot,
    LotEvent,
    LotState,
    MonthProceeds,
    ExpenseResult,
    YearProceeds,
    YearResult,
)


class HoldingMode(Enum):
    """How to count days held in the purchase month."""

    FULL_MONTH = "full_month"
    PRORATE = "prorate"


@dataclass
class PeriodResult:
    """Result of computing Steps 1-6 for a single contiguous period."""

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
        if adj_btc == 0:
            total_btc_sold = Decimal("0")
            cost_basis_of_sold = Decimal("0")
        else:
            btc_sold_per_share = proration * monthly_btc_sold_per_share
            total_btc_sold = btc_sold_per_share * shares
            # Step 3: use adj_basis (matched pair with adj_btc)
            cost_basis_of_sold = (total_btc_sold / adj_btc) * adj_basis

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
    """Input parameters for computing a single lot-month."""

    lot: Lot
    year: int
    month: int
    adj_btc: Decimal
    adj_basis: Decimal
    shares: Decimal
    month_proceeds: MonthProceeds


@dataclass
class LotMonthOutput:
    """Output from computing a single lot-month."""

    month_result: ExpenseResult
    dispositions: list[Disposition]
    new_state: LotState


@dataclass
class _SellPhaseResult:
    adj_btc: Decimal
    adj_basis: Decimal
    shares: Decimal
    total_btc_sold: Decimal
    total_cost_basis: Decimal
    total_expense: Decimal
    total_gain_loss: Decimal
    dispositions: list[Disposition]


def _handle_sells_full_month(
    *,
    sell_events: list[LotEvent],
    inp: LotMonthInput,
    adj_btc: Decimal,
    adj_basis: Decimal,
    shares: Decimal,
    full_days_held: Decimal,
    days_in_month: Decimal,
) -> _SellPhaseResult:
    """FULL_MONTH: dispositions first, then expense on surviving shares."""
    total_btc_sold = Decimal("0")
    total_cost_basis = Decimal("0")
    total_expense = Decimal("0")
    total_gain_loss = Decimal("0")
    dispositions: list[Disposition] = []

    for event in sell_events:
        if shares <= 0 or event.shares > shares:
            raise ValueError(
                f"Sell of {event.shares} shares exceeds remaining {shares} shares for lot {inp.lot.id}"
            )
        disposed_btc = adj_btc * (event.shares / shares)
        disposed_basis = adj_basis * (event.shares / shares)
        dispositions.append(
            Disposition(
                lot_id=inp.lot.id,
                disposition_id=event.disposition_id,
                date_sold=event.date,
                shares_sold=event.shares,
                proceeds=event.proceeds,
                disposed_btc=disposed_btc,
                disposed_basis=disposed_basis,
                gain_loss=event.proceeds - disposed_basis,
            )
        )
        adj_btc -= disposed_btc
        adj_basis -= disposed_basis
        shares -= event.shares

    # Expense is computed only on surviving shares (after all dispositions).
    # This matches observed 1099 behavior: disposed shares do not generate
    # trust expense; only shares still held at month-end participate.
    if shares > 0:
        pr = compute_period(
            days_held=full_days_held,
            days_in_month=days_in_month,
            shares=shares,
            adj_btc=adj_btc,
            adj_basis=adj_basis,
            monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
            monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
        )
        total_btc_sold += pr.total_btc_sold
        total_cost_basis += pr.cost_basis_of_sold
        total_expense += pr.total_expense
        total_gain_loss += pr.gain_loss
        adj_btc = pr.adj_btc
        adj_basis = pr.adj_basis

    return _SellPhaseResult(
        adj_btc=adj_btc,
        adj_basis=adj_basis,
        shares=shares,
        total_btc_sold=total_btc_sold,
        total_cost_basis=total_cost_basis,
        total_expense=total_expense,
        total_gain_loss=total_gain_loss,
        dispositions=dispositions,
    )


def _handle_sells_prorate(
    *,
    sell_events: list[LotEvent],
    inp: LotMonthInput,
    adj_btc: Decimal,
    adj_basis: Decimal,
    shares: Decimal,
    days_in_month: Decimal,
    period_start: date,
    month_end: date,
) -> _SellPhaseResult:
    """PRORATE: split month into phases around each sell."""
    total_btc_sold = Decimal("0")
    total_cost_basis = Decimal("0")
    total_expense = Decimal("0")
    total_gain_loss = Decimal("0")
    dispositions: list[Disposition] = []

    current_start = period_start
    for event in sell_events:
        pre_days = Decimal(str((event.date - current_start).days))
        if pre_days > 0:
            pr = compute_period(
                days_held=pre_days,
                days_in_month=days_in_month,
                shares=shares,
                adj_btc=adj_btc,
                adj_basis=adj_basis,
                monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
                monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
            )
            total_btc_sold += pr.total_btc_sold
            total_cost_basis += pr.cost_basis_of_sold
            total_expense += pr.total_expense
            total_gain_loss += pr.gain_loss
            adj_btc = pr.adj_btc
            adj_basis = pr.adj_basis

        if shares <= 0 or event.shares > shares:
            raise ValueError(
                f"Sell of {event.shares} shares exceeds remaining {shares} shares for lot {inp.lot.id}"
            )
        disposed_btc = adj_btc * (event.shares / shares)
        disposed_basis = adj_basis * (event.shares / shares)
        dispositions.append(
            Disposition(
                lot_id=inp.lot.id,
                disposition_id=event.disposition_id,
                date_sold=event.date,
                shares_sold=event.shares,
                proceeds=event.proceeds,
                disposed_btc=disposed_btc,
                disposed_basis=disposed_basis,
                gain_loss=event.proceeds - disposed_basis,
            )
        )
        adj_btc -= disposed_btc
        adj_basis -= disposed_basis
        shares -= event.shares
        current_start = event.date

    if shares > 0:
        # +1: include the sell date itself in the post-sell phase, since
        # the shareholder still held the remaining shares on that day.
        post_days = Decimal(str((month_end - current_start).days)) + 1
        if post_days > 0:
            pr = compute_period(
                days_held=post_days,
                days_in_month=days_in_month,
                shares=shares,
                adj_btc=adj_btc,
                adj_basis=adj_basis,
                monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
                monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
            )
            total_btc_sold += pr.total_btc_sold
            total_cost_basis += pr.cost_basis_of_sold
            total_expense += pr.total_expense
            total_gain_loss += pr.gain_loss
            adj_btc = pr.adj_btc
            adj_basis = pr.adj_basis

    return _SellPhaseResult(
        adj_btc=adj_btc,
        adj_basis=adj_basis,
        shares=shares,
        total_btc_sold=total_btc_sold,
        total_cost_basis=total_cost_basis,
        total_expense=total_expense,
        total_gain_loss=total_gain_loss,
        dispositions=dispositions,
    )


def _month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def _month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def _holding_term(purchase_date: date, sell_date: date) -> HoldingTerm:
    """Classify as LONG_TERM if held more than one year per IRS rules."""
    try:
        anniversary = purchase_date.replace(year=purchase_date.year + 1)
    except ValueError:
        # Feb 29 -> Feb 28; long-term starts March 1
        anniversary = purchase_date.replace(year=purchase_date.year + 1, day=28)
    if sell_date > anniversary:
        return HoldingTerm.LONG_TERM
    return HoldingTerm.SHORT_TERM


def compute_lot_month(
    inp: LotMonthInput, *, holding_mode: HoldingMode = HoldingMode.FULL_MONTH
) -> LotMonthOutput | None:
    """Compute one month for one lot, handling mid-month sells.

    FULL_MONTH (default): lots purchased mid-month use the full month as their
    holding period, matching Fidelity's 1099 calculations.
    PRORATE: prorate based on actual days held, as shown in the WHFIT document example.
    """
    month_end = _month_end(inp.year, inp.month)
    month_start_date = _month_start(inp.year, inp.month)
    days_in_month = Decimal(str(calendar.monthrange(inp.year, inp.month)[1]))

    # Check if lot is active this month
    if inp.lot.purchase_date > month_end:
        return None

    holding_term = _holding_term(inp.lot.purchase_date, month_end)

    # Determine base days_held for the full month
    if inp.lot.purchase_date >= month_start_date:
        if holding_mode is HoldingMode.PRORATE:
            # First month: prorate from purchase date
            full_days_held = Decimal(str((month_end - inp.lot.purchase_date).days))
            if full_days_held == 0:
                return None  # Purchased on last day, starts next month
            period_start = inp.lot.purchase_date
        else:
            full_days_held = days_in_month
            period_start = month_start_date
    else:
        full_days_held = days_in_month
        period_start = month_start_date

    # Find sell events in this month for this lot
    sell_events = [
        e
        for e in inp.lot.events
        if e.type == "sell" and e.date.year == inp.year and e.date.month == inp.month
    ]
    sell_events.sort(key=lambda e: e.date)

    adj_btc = inp.adj_btc
    adj_basis = inp.adj_basis
    shares = inp.shares

    if not sell_events:
        # Simple case: no sells, run full period
        pr = compute_period(
            days_held=full_days_held,
            days_in_month=days_in_month,
            shares=shares,
            adj_btc=adj_btc,
            adj_basis=adj_basis,
            monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
            monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
        )
        return LotMonthOutput(
            month_result=ExpenseResult(
                sell_date=month_end,
                days_held=full_days_held,
                days_in_month=days_in_month,
                shares=shares,
                total_btc_sold=pr.total_btc_sold,
                cost_basis_of_sold=pr.cost_basis_of_sold,
                total_expense=pr.total_expense,
                gain_loss=pr.gain_loss,
                adj_btc=pr.adj_btc,
                adj_basis=pr.adj_basis,
                holding_term=holding_term,
            ),
            dispositions=[],
            new_state=LotState(
                adj_btc=pr.adj_btc, adj_basis=pr.adj_basis, shares=shares
            ),
        )

    if holding_mode is HoldingMode.FULL_MONTH:
        result = _handle_sells_full_month(
            sell_events=sell_events,
            inp=inp,
            adj_btc=adj_btc,
            adj_basis=adj_basis,
            shares=shares,
            full_days_held=full_days_held,
            days_in_month=days_in_month,
        )
    else:
        result = _handle_sells_prorate(
            sell_events=sell_events,
            inp=inp,
            adj_btc=adj_btc,
            adj_basis=adj_basis,
            shares=shares,
            days_in_month=days_in_month,
            period_start=period_start,
            month_end=month_end,
        )

    return LotMonthOutput(
        month_result=ExpenseResult(
            sell_date=month_end,
            days_held=full_days_held,
            days_in_month=days_in_month,
            shares=inp.shares,
            total_btc_sold=result.total_btc_sold,
            cost_basis_of_sold=result.total_cost_basis,
            total_expense=result.total_expense,
            gain_loss=result.total_gain_loss,
            adj_btc=result.adj_btc,
            adj_basis=result.adj_basis,
            holding_term=holding_term,
        ),
        dispositions=result.dispositions,
        new_state=LotState(
            adj_btc=result.adj_btc, adj_basis=result.adj_basis, shares=result.shares
        ),
    )


def compute_year(
    *,
    lots: list[Lot],
    proceeds: YearProceeds,
    prior_state: dict[str, LotState] | None,
    year: int,
    holding_mode: HoldingMode = HoldingMode.FULL_MONTH,
) -> YearResult:
    """Compute all lots for a full year, chaining monthly state."""
    all_lot_results: dict[str, list[ExpenseResult]] = {}
    all_dispositions: list[Disposition] = []
    end_states: dict[str, LotState] = {}

    for lot in lots:

        # Determine initial state for this lot
        if lot.purchase_date.year == year:
            # New lot this year
            initial_btc = lot.btc_per_share_on_purchase * lot.original_shares
            state = LotState(
                adj_btc=initial_btc,
                adj_basis=lot.total_cost,
                shares=lot.original_shares,
            )
        elif prior_state and lot.id in prior_state:
            state = prior_state[lot.id]
        else:
            # Lot from a prior year without prior state
            if lot.purchase_date.year < year:
                raise ValueError(
                    f"Lot {lot.id} (purchased {lot.purchase_date.isoformat()}) "
                    f"requires {year - 1} results before computing {year}"
                )
            continue  # Future lot, skip

        # Skip fully liquidated lots
        if state.shares == 0:
            end_states[lot.id] = state
            continue

        expense_results: list[ExpenseResult] = []

        for month in range(1, 13):
            month_end = _month_end(year, month)

            # Find month-end proceeds (may be absent = zero expense)
            mp = proceeds.monthly.get(month_end)
            if mp is None:
                mp = MonthProceeds(
                    btc_sold_per_share=Decimal("0"),
                    proceeds_per_share_usd=Decimal("0"),
                )

            output = compute_lot_month(
                LotMonthInput(
                    lot=lot,
                    year=year,
                    month=month,
                    adj_btc=state.adj_btc,
                    adj_basis=state.adj_basis,
                    shares=state.shares,
                    month_proceeds=mp,
                ),
                holding_mode=holding_mode,
            )

            if output is None:
                continue

            expense_results.append(output.month_result)
            all_dispositions.extend(output.dispositions)
            state = output.new_state

        all_lot_results[lot.id] = expense_results
        end_states[lot.id] = state

    # Compute annual summary
    total_expense = sum(
        (mr.total_expense for results in all_lot_results.values() for mr in results),
        Decimal("0"),
    )
    total_gain = sum(
        (mr.gain_loss for results in all_lot_results.values() for mr in results),
        Decimal("0"),
    )

    return YearResult(
        year=year,
        lot_results=all_lot_results,
        dispositions=all_dispositions,
        end_states=end_states,
        total_investment_expense=total_expense,
        total_reportable_gain=total_gain,
        total_cost_basis_of_expense=total_expense - total_gain,
    )

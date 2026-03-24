"""Validate engine invariants using real 2024 lot and proceeds data.

These tests verify mathematical properties that must hold regardless of
the specific numeric values — no spreadsheet comparisons.
"""

from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import (
    Lot,
    MonthProceeds,
    YearProceeds,
)
from fbtc_taxgrinder.engine.compute import compute_year

# 2024 monthly proceeds (Aug-Dec only, Jan-Jul had zero sales)
PROCEEDS_2024 = YearProceeds(
    daily={
        date(2024, 1, 25): Decimal("0.00087448"),
        date(2024, 2, 17): Decimal("0.00087448"),
        date(2024, 2, 23): Decimal("0.00087448"),
        date(2024, 3, 6): Decimal("0.00087448"),
        date(2024, 3, 19): Decimal("0.00087448"),
        date(2024, 3, 22): Decimal("0.00087448"),
        date(2024, 4, 18): Decimal("0.00087448"),
        date(2024, 6, 5): Decimal("0.00087448"),
        date(2024, 8, 19): Decimal("0.00087437"),
        date(2024, 9, 9): Decimal("0.00087425"),
        date(2024, 10, 17): Decimal("0.00087401"),
        date(2024, 11, 5): Decimal("0.00087391"),
    },
    monthly={
        date(2024, 8, 31): MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01070327"),
        ),
        date(2024, 9, 30): MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01124247"),
        ),
        date(2024, 10, 31): MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01236501"),
        ),
        date(2024, 11, 30): MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01729430"),
        ),
        date(2024, 12, 31): MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01722667"),
        ),
    },
    source="test",
)

ALL_LOTS_2024 = [
    Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-2",
        purchase_date=date(2024, 2, 17),
        original_shares=Decimal("2"),
        price_per_share=Decimal("45.81"),
        total_cost=Decimal("91.62"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-3",
        purchase_date=date(2024, 2, 23),
        original_shares=Decimal("9"),
        price_per_share=Decimal("44.85"),
        total_cost=Decimal("403.65"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-4",
        purchase_date=date(2024, 3, 6),
        original_shares=Decimal("42"),
        price_per_share=Decimal("58.315"),
        total_cost=Decimal("2449.23"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-5",
        purchase_date=date(2024, 3, 19),
        original_shares=Decimal("1"),
        price_per_share=Decimal("56.639"),
        total_cost=Decimal("56.639"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-6",
        purchase_date=date(2024, 3, 22),
        original_shares=Decimal("1"),
        price_per_share=Decimal("56.18"),
        total_cost=Decimal("56.18"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-7",
        purchase_date=date(2024, 4, 18),
        original_shares=Decimal("1"),
        price_per_share=Decimal("55.82"),
        total_cost=Decimal("55.82"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-8",
        purchase_date=date(2024, 4, 18),
        original_shares=Decimal("54"),
        price_per_share=Decimal("55.6097"),
        total_cost=Decimal("3002.9238"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-9",
        purchase_date=date(2024, 6, 5),
        original_shares=Decimal("4"),
        price_per_share=Decimal("62.2379"),
        total_cost=Decimal("248.9516"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-10",
        purchase_date=date(2024, 8, 19),
        original_shares=Decimal("1"),
        price_per_share=Decimal("51.3995"),
        total_cost=Decimal("51.3995"),
        btc_per_share_on_purchase=Decimal("0.00087437"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-11",
        purchase_date=date(2024, 8, 19),
        original_shares=Decimal("5"),
        price_per_share=Decimal("51.3669"),
        total_cost=Decimal("256.8345"),
        btc_per_share_on_purchase=Decimal("0.00087437"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-12",
        purchase_date=date(2024, 9, 9),
        original_shares=Decimal("126"),
        price_per_share=Decimal("49.50"),
        total_cost=Decimal("6237.00"),
        btc_per_share_on_purchase=Decimal("0.00087425"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-13",
        purchase_date=date(2024, 9, 9),
        original_shares=Decimal("86"),
        price_per_share=Decimal("49.4297"),
        total_cost=Decimal("4250.9542"),
        btc_per_share_on_purchase=Decimal("0.00087425"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-14",
        purchase_date=date(2024, 10, 17),
        original_shares=Decimal("82"),
        price_per_share=Decimal("58.62"),
        total_cost=Decimal("4806.84"),
        btc_per_share_on_purchase=Decimal("0.00087401"),
        source_file="t",
        events=[],
    ),
    Lot(
        id="lot-15",
        purchase_date=date(2024, 11, 5),
        original_shares=Decimal("17"),
        price_per_share=Decimal("61.2986"),
        total_cost=Decimal("1042.0762"),
        btc_per_share_on_purchase=Decimal("0.00087391"),
        source_file="t",
        events=[],
    ),
]


def _compute_2024():
    return compute_year(
        lots=ALL_LOTS_2024,
        proceeds=PROCEEDS_2024,
        prior_state=None,
        year=2024,
    )


def test_adj_btc_monotonically_decreases():
    """Each month's adj_btc must be <= the previous month's (BTC is only sold, never added)."""
    result = _compute_2024()
    for lot_id, months in result.lot_results.items():
        for i in range(1, len(months)):
            assert months[i].adj_btc <= months[i - 1].adj_btc, (
                f"{lot_id} month {months[i].sell_date}: adj_btc increased "
                f"from {months[i-1].adj_btc} to {months[i].adj_btc}"
            )


def test_adj_basis_monotonically_decreases():
    """Each month's adj_basis must be <= the previous month's (basis is only consumed)."""
    result = _compute_2024()
    for lot_id, months in result.lot_results.items():
        for i in range(1, len(months)):
            assert months[i].adj_basis <= months[i - 1].adj_basis, (
                f"{lot_id} month {months[i].sell_date}: adj_basis increased "
                f"from {months[i-1].adj_basis} to {months[i].adj_basis}"
            )


def test_end_state_btc_less_than_initial():
    """Every lot's year-end adj_btc must be less than initial BTC (expenses were deducted)."""
    result = _compute_2024()
    for lot in ALL_LOTS_2024:
        initial_btc = lot.btc_per_share_on_purchase * lot.original_shares
        end_state = result.end_states[lot.id]
        assert (
            end_state.adj_btc < initial_btc
        ), f"{lot.id}: end adj_btc {end_state.adj_btc} >= initial {initial_btc}"


def test_end_state_basis_less_than_initial():
    """Every lot's year-end adj_basis must be less than initial cost."""
    result = _compute_2024()
    for lot in ALL_LOTS_2024:
        end_state = result.end_states[lot.id]
        assert (
            end_state.adj_basis < lot.total_cost
        ), f"{lot.id}: end adj_basis {end_state.adj_basis} >= initial {lot.total_cost}"


def test_total_expense_equals_sum_of_monthly():
    """Year total_investment_expense must equal sum of all monthly total_expense values."""
    result = _compute_2024()
    monthly_sum = sum(
        mr.total_expense for months in result.lot_results.values() for mr in months
    )
    assert result.total_investment_expense == monthly_sum


def test_total_gain_equals_sum_of_monthly():
    """Year total_reportable_gain must equal sum of all monthly gain_loss values."""
    result = _compute_2024()
    monthly_sum = sum(
        mr.gain_loss for months in result.lot_results.values() for mr in months
    )
    assert result.total_reportable_gain == monthly_sum


def test_cost_basis_identity():
    """total_cost_basis_of_expense must equal total_expense - total_gain."""
    result = _compute_2024()
    assert result.total_cost_basis_of_expense == (
        result.total_investment_expense - result.total_reportable_gain
    )


def test_all_lots_produce_results():
    """All 15 lots should have at least one month of results."""
    result = _compute_2024()
    for lot in ALL_LOTS_2024:
        assert lot.id in result.lot_results, f"{lot.id} missing from results"
        assert len(result.lot_results[lot.id]) > 0, f"{lot.id} has no monthly results"


def test_prorated_lots_have_fewer_active_months():
    """Lots purchased mid-Aug+ should have fewer active months than Jan lots."""
    result = _compute_2024()
    jan_lot_months = len(result.lot_results["lot-1"])  # purchased Jan 25
    nov_lot_months = len(result.lot_results["lot-15"])  # purchased Nov 5
    assert nov_lot_months < jan_lot_months, (
        f"lot-15 (Nov purchase) has {nov_lot_months} months, "
        f"lot-1 (Jan purchase) has {jan_lot_months} months"
    )


def test_no_negative_values():
    """adj_btc, adj_basis, total_btc_sold, cost_basis_of_sold, total_expense must all be >= 0."""
    result = _compute_2024()
    for lot_id, months in result.lot_results.items():
        for mr in months:
            assert mr.adj_btc >= 0, f"{lot_id} month {mr.sell_date}: negative adj_btc"
            assert (
                mr.adj_basis >= 0
            ), f"{lot_id} month {mr.sell_date}: negative adj_basis"
            assert (
                mr.total_btc_sold >= 0
            ), f"{lot_id} month {mr.sell_date}: negative total_btc_sold"
            assert (
                mr.cost_basis_of_sold >= 0
            ), f"{lot_id} month {mr.sell_date}: negative cost_basis"
            assert (
                mr.total_expense >= 0
            ), f"{lot_id} month {mr.sell_date}: negative total_expense"


def test_deterministic():
    """Running compute_year twice with same inputs produces identical results."""
    r1 = _compute_2024()
    r2 = _compute_2024()
    for lot in ALL_LOTS_2024:
        months1 = r1.lot_results[lot.id]
        months2 = r2.lot_results[lot.id]
        assert len(months1) == len(months2)
        for m1, m2 in zip(months1, months2):
            assert m1.adj_btc == m2.adj_btc
            assert m1.adj_basis == m2.adj_basis
            assert m1.total_expense == m2.total_expense

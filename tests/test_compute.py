from decimal import Decimal
from datetime import date
import pytest
from fbtc_taxgrinder.engine.compute import HoldingMode, compute_period, compute_lot_month, compute_year, LotMonthInput
from fbtc_taxgrinder.models import Lot, LotEvent, LotState, MonthProceeds, YearProceeds


def test_compute_period_full_month():
    """Lot-1, August 2024: 204 shares, full month (31 days), first expense month."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("204"),
        adj_btc=Decimal("0.17839392"),       # 0.00087448 * 204
        adj_basis=Decimal("7101.24"),

        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    # Step 2: btc_sold_per_share = (31/31) * 0.00000018 = 0.00000018
    #         total_btc_sold = 0.00000018 * 204 = 0.00003672
    assert result.total_btc_sold == Decimal("0.00000018") * Decimal("204")
    # Step 4: total_expense = 0.01070327 * 204 = 2.18346708
    assert result.total_expense == Decimal("0.01070327") * Decimal("204")
    # Step 6: adj_btc = 0.17839392 - 0.00003672
    assert result.adj_btc == Decimal("0.17839392") - Decimal("0.00003672")


def test_compute_period_zero_expense():
    """Month with no BTC sold (Jan-Jul 2024)."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("204"),
        adj_btc=Decimal("0.17839392"),
        adj_basis=Decimal("7101.24"),

        monthly_btc_sold_per_share=Decimal("0"),
        monthly_proceeds_per_share_usd=Decimal("0"),
    )
    assert result.total_btc_sold == Decimal("0")
    assert result.total_expense == Decimal("0")
    assert result.gain_loss == Decimal("0")
    assert result.adj_btc == Decimal("0.17839392")
    assert result.adj_basis == Decimal("7101.24")


def test_compute_period_prorated():
    """Lot purchased Aug 19, first month Aug: days_held = 12 out of 31."""
    result = compute_period(
        days_held=Decimal("12"),
        days_in_month=Decimal("31"),
        shares=Decimal("1"),
        adj_btc=Decimal("0.00087437"),
        adj_basis=Decimal("51.3995"),

        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    # btc_sold = (12/31) * 0.00000018 * 1
    expected_btc_sold = Decimal("12") / Decimal("31") * Decimal("0.00000018")
    assert result.total_btc_sold == expected_btc_sold
    # expense = (12/31) * 0.01070327 * 1
    expected_expense = Decimal("12") / Decimal("31") * Decimal("0.01070327")
    assert result.total_expense == expected_expense


def test_compute_period_zero_shares():
    """shares == 0 should short-circuit and preserve adj values."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("0"),
        adj_btc=Decimal("0.001"),
        adj_basis=Decimal("50.00"),

        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    assert result.total_btc_sold == Decimal("0")
    assert result.total_expense == Decimal("0")
    assert result.adj_btc == Decimal("0.001")
    assert result.adj_basis == Decimal("50.00")


def test_compute_period_btc_sold_zero_proceeds():
    """BTC sold but proceeds are zero — negative gain_loss (pure cost)."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("10"),
        adj_btc=Decimal("0.0087448"),
        adj_basis=Decimal("500.00"),

        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0"),
    )
    assert result.total_btc_sold == Decimal("0.00000018") * Decimal("10")
    assert result.total_expense == Decimal("0")
    assert result.cost_basis_of_sold > Decimal("0")
    assert result.gain_loss < Decimal("0")


def test_compute_period_cost_basis_calculation():
    """Verify Step 3: cost_basis = (total_btc_sold / adj_btc) * adj_basis."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("204"),
        adj_btc=Decimal("0.17839392"),
        adj_basis=Decimal("7101.24"),

        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    total_btc_sold = Decimal("0.00000018") * Decimal("204")
    expected_cost_basis = (total_btc_sold / Decimal("0.17839392")) * Decimal("7101.24")
    assert result.cost_basis_of_sold == expected_cost_basis


def test_month_state_chaining():
    """Output state from month N feeds correctly as input to month N+1."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv", events=[],
    )
    mp = MonthProceeds(
        btc_sold_per_share=Decimal("0.00000018"),
        proceeds_per_share_usd=Decimal("0.01070327"),
    )

    # Month 1
    r1 = compute_lot_month(LotMonthInput(
        lot=lot, year=2024, month=8,
        adj_btc=Decimal("0.17839392"),
        adj_basis=Decimal("7101.24"),
        shares=Decimal("204"),
        month_proceeds=mp,
    ))
    assert r1 is not None

    # Month 2 uses month 1's output state
    r2 = compute_lot_month(LotMonthInput(
        lot=lot, year=2024, month=9,
        adj_btc=r1.new_state.adj_btc,
        adj_basis=r1.new_state.adj_basis,
        shares=r1.new_state.shares,
        month_proceeds=mp,
    ))
    assert r2 is not None
    # adj_btc should decrease further
    assert r2.new_state.adj_btc < r1.new_state.adj_btc
    assert r2.new_state.adj_basis < r1.new_state.adj_basis


def test_compute_period_gain_loss_sign():
    """When expense > cost_basis, gain_loss is positive (net gain).
    When expense < cost_basis, gain_loss is negative (net loss)."""
    # Large proceeds relative to BTC sold -> positive gain
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("204"),
        adj_btc=Decimal("0.17839392"),
        adj_basis=Decimal("7101.24"),

        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    assert result.gain_loss > Decimal("0")
    assert result.gain_loss == result.total_expense - result.cost_basis_of_sold


def test_compute_period_adj_basis_tracks_cost_basis():
    """adj_basis should decrease by exactly cost_basis_of_sold."""
    adj_basis = Decimal("7101.24")
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("204"),
        adj_btc=Decimal("0.17839392"),
        adj_basis=adj_basis,

        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    assert result.adj_basis == adj_basis - result.cost_basis_of_sold


def test_compute_period_single_share():
    """Single share lot — ensures no rounding weirdness with share=1."""
    result = compute_period(
        days_held=Decimal("30"),
        days_in_month=Decimal("30"),
        shares=Decimal("1"),
        adj_btc=Decimal("0.00087448"),
        adj_basis=Decimal("34.81"),

        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    assert result.total_btc_sold == Decimal("0.00000018")
    assert result.total_expense == Decimal("0.01070327")


def test_cost_basis_uses_adj_basis_not_original():
    """Step 3 must use adj_basis (not original cost) for correct multi-year behavior.
    When adj_basis < original cost, using original cost would overstate cost_basis."""
    # Simulate year 2: adj values are less than original
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("100"),
        adj_btc=Decimal("0.08"),       # reduced from original 0.0874
        adj_basis=Decimal("4500.00"),  # reduced from original 5000.00
        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    total_btc_sold = Decimal("0.00000018") * Decimal("100")
    # Should use adj_basis=4500, NOT some original cost
    expected = (total_btc_sold / Decimal("0.08")) * Decimal("4500.00")
    assert result.cost_basis_of_sold == expected


def test_sell_then_full_month_state_chain():
    """After a sell month, the next full month should use reduced shares/btc/basis."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("100"), price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell", date=date(2025, 3, 15),
                shares=Decimal("40"), price_per_share=Decimal("60.00"),
                proceeds=Decimal("2400.00"), disposition_id="lot-1-sell-1",
            ),
        ],
    )
    mp = MonthProceeds(
        btc_sold_per_share=Decimal("0.00000018"),
        proceeds_per_share_usd=Decimal("0.01509769"),
    )

    # March: has sell
    r1 = compute_lot_month(LotMonthInput(
        lot=lot, year=2025, month=3,
        adj_btc=Decimal("0.08700000"),
        adj_basis=Decimal("4950.00"),
        shares=Decimal("100"),
        month_proceeds=mp,
    ))
    assert r1 is not None
    assert r1.new_state.shares == Decimal("60")

    # April: full month with reduced shares
    r2 = compute_lot_month(LotMonthInput(
        lot=lot, year=2025, month=4,
        adj_btc=r1.new_state.adj_btc,
        adj_basis=r1.new_state.adj_basis,
        shares=r1.new_state.shares,
        month_proceeds=mp,
    ))
    assert r2 is not None
    assert r2.month_result.shares == Decimal("60")  # starting shares
    assert r2.new_state.shares == Decimal("60")  # no sell this month


def test_compute_year_single_lot_single_month():
    """Simplest case: one lot, one active month (Aug 2024), full month."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv", events=[],
    )
    proceeds = YearProceeds(
        daily={date(2024, 1, 25): Decimal("0.00087448")},
        monthly={
            date(2024, 8, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        },
        source="test",
    )
    result = compute_year(
        lots=[lot],
        proceeds=proceeds,
        prior_state=None,
        year=2024,
    )
    assert "lot-1" in result.lot_results
    # Aug is month 8, should be the only result with nonzero expense
    aug = [r for r in result.lot_results["lot-1"] if r.sell_date == date(2024, 8, 31)]
    assert len(aug) == 1
    assert aug[0].shares == Decimal("204")


def test_holding_mode_flag():
    """Default uses full month; PRORATE mode prorates from purchase date."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 15),
        original_shares=Decimal("100"), price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.001"),
        source_file="test.csv", events=[],
    )
    mp = MonthProceeds(
        btc_sold_per_share=Decimal("0.00000018"),
        proceeds_per_share_usd=Decimal("0.01070327"),
    )
    inp = LotMonthInput(
        lot=lot, year=2024, month=1,
        adj_btc=Decimal("0.1"),
        adj_basis=Decimal("5000.00"),
        shares=Decimal("100"),
        month_proceeds=mp,
    )

    # Default: full month (31 days)
    r_full = compute_lot_month(inp)
    assert r_full is not None
    assert r_full.month_result.days_held == Decimal("31")

    # PRORATE mode: prorate from purchase date (16 days out of 31)
    r_prorated = compute_lot_month(inp, holding_mode=HoldingMode.PRORATE)
    assert r_prorated is not None
    assert r_prorated.month_result.days_held == Decimal("16")

    # Full month should produce higher expense
    assert r_full.month_result.total_expense > r_prorated.month_result.total_expense


def test_compute_period_zero_adj_btc():
    """C2: When adj_btc is zero but monthly_btc_sold_per_share is nonzero,
    should return zeros instead of dividing by zero."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("100"),
        adj_btc=Decimal("0"),
        adj_basis=Decimal("500.00"),
        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    assert result.total_btc_sold == Decimal("0")
    assert result.cost_basis_of_sold == Decimal("0")
    # Expense should still be computed (it doesn't depend on adj_btc)
    assert result.total_expense == Decimal("0.01070327") * Decimal("100")
    # gain_loss = expense - cost_basis_of_sold = expense - 0
    assert result.gain_loss == result.total_expense
    # adj_btc should remain 0 (0 - 0)
    assert result.adj_btc == Decimal("0")
    assert result.adj_basis == Decimal("500.00")


def test_compute_year_with_prior_state():
    """Multi-year state chaining: 2025 uses carried-forward state from 2024."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv", events=[],
    )
    proceeds_2024 = YearProceeds(
        daily={date(2024, 1, 25): Decimal("0.00087448")},
        monthly={
            date(2024, 8, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        },
        source="test",
    )

    # Compute 2024
    result_2024 = compute_year(
        lots=[lot], proceeds=proceeds_2024, prior_state=None, year=2024,
    )
    end_state = result_2024.end_states["lot-1"]

    # Verify 2024 state differs from original (expense reduced adj values)
    original_btc = Decimal("0.00087448") * Decimal("204")
    assert end_state.adj_btc < original_btc
    assert end_state.adj_basis < Decimal("7101.24")
    assert end_state.shares == Decimal("204")

    # Create 2025 proceeds with expense in March
    proceeds_2025 = YearProceeds(
        daily={},
        monthly={
            date(2025, 3, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000020"),
                proceeds_per_share_usd=Decimal("0.01509769"),
            ),
        },
        source="test",
    )

    # Compute 2025 with prior state from 2024
    result_2025 = compute_year(
        lots=[lot], proceeds=proceeds_2025,
        prior_state=result_2024.end_states, year=2025,
    )
    end_state_2025 = result_2025.end_states["lot-1"]

    # 2025 should start from carried-forward values, not originals
    # After 2025 expense, adj values should be even lower than 2024 end
    assert end_state_2025.adj_btc < end_state.adj_btc
    assert end_state_2025.adj_basis < end_state.adj_basis
    assert end_state_2025.shares == Decimal("204")

    # Verify 2025 March result used carried-forward state
    march_results = [r for r in result_2025.lot_results["lot-1"] if r.sell_date == date(2025, 3, 31)]
    assert len(march_results) == 1
    # The adj_btc at end of March should be less than what 2024 ended with
    assert march_results[0].adj_btc < end_state.adj_btc


def test_compute_year_chain_validation_error():
    """Lot from 2024 computing 2026 without 2025 state should error."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv", events=[],
    )
    proceeds = YearProceeds(
        daily={}, monthly={}, source="test",
    )
    with pytest.raises(ValueError, match="requires 2025 results"):
        compute_year(
            lots=[lot],
            proceeds=proceeds,
            prior_state=None,
            year=2026,
        )


def test_compute_year_future_lot_skipped():
    """A lot purchased in a future year should be silently skipped."""
    lot_current = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("100"), price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.001"),
        source_file="test.csv", events=[],
    )
    lot_future = Lot(
        id="lot-2", purchase_date=date(2025, 6, 15),
        original_shares=Decimal("50"), price_per_share=Decimal("60.00"),
        total_cost=Decimal("3000.00"),
        btc_per_share_on_purchase=Decimal("0.0009"),
        source_file="test.csv", events=[],
    )
    proceeds = YearProceeds(
        daily={date(2024, 1, 25): Decimal("0.001")},
        monthly={},
        source="test",
    )
    result = compute_year(
        lots=[lot_current, lot_future],
        proceeds=proceeds,
        prior_state=None,
        year=2024,
    )
    # lot-1 should be computed, lot-2 should be skipped entirely
    assert "lot-1" in result.end_states
    assert "lot-2" not in result.end_states


def test_compute_year_fully_liquidated_lot_preserved():
    """A lot with shares=0 in prior state should be preserved in end_states but not computed."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("100"), price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.001"),
        source_file="test.csv", events=[],
    )
    prior = {
        "lot-1": LotState(
            adj_btc=Decimal("0.00001"),
            adj_basis=Decimal("0.50"),
            shares=Decimal("0"),
        ),
    }
    proceeds = YearProceeds(
        daily={}, monthly={}, source="test",
    )
    result = compute_year(
        lots=[lot], proceeds=proceeds,
        prior_state=prior, year=2025,
    )
    # Should be in end_states with same values
    assert "lot-1" in result.end_states
    assert result.end_states["lot-1"].shares == Decimal("0")
    # Should not have any expense results
    assert "lot-1" not in result.lot_results


def test_compute_year_prior_state_lot_missing():
    """Prior state provided but lot ID not in it — should raise ValueError."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("100"), price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.001"),
        source_file="test.csv", events=[],
    )
    # prior_state exists but doesn't contain lot-1
    prior = {
        "lot-other": LotState(
            adj_btc=Decimal("0.001"),
            adj_basis=Decimal("500.00"),
            shares=Decimal("100"),
        ),
    }
    proceeds = YearProceeds(
        daily={}, monthly={}, source="test",
    )
    with pytest.raises(ValueError, match="requires 2024 results"):
        compute_year(
            lots=[lot], proceeds=proceeds,
            prior_state=prior, year=2025,
        )

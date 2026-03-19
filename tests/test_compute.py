from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.engine.compute import compute_period, compute_lot_month, LotMonthInput
from fbtc_taxgrinder.models import Lot, LotEvent, MonthProceeds


def test_compute_period_full_month():
    """Lot-1, August 2024: 204 shares, full month (31 days), first expense month."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("204"),
        adj_btc=Decimal("0.17839392"),       # 0.00087448 * 204
        adj_basis=Decimal("7101.24"),
        original_total_cost=Decimal("7101.24"),
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
        original_total_cost=Decimal("7101.24"),
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
        original_total_cost=Decimal("51.3995"),
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
        original_total_cost=Decimal("50.00"),
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
        original_total_cost=Decimal("500.00"),
        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0"),
    )
    assert result.total_btc_sold == Decimal("0.00000018") * Decimal("10")
    assert result.total_expense == Decimal("0")
    assert result.cost_basis_of_sold > Decimal("0")
    assert result.gain_loss < Decimal("0")


def test_compute_period_cost_basis_calculation():
    """Verify Step 3: cost_basis = (total_btc_sold / adj_btc) * original_total_cost."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("204"),
        adj_btc=Decimal("0.17839392"),
        adj_basis=Decimal("7101.24"),
        original_total_cost=Decimal("7101.24"),
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
        original_total_cost=Decimal("7101.24"),
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
        original_total_cost=Decimal("7101.24"),
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
        original_total_cost=Decimal("34.81"),
        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    assert result.total_btc_sold == Decimal("0.00000018")
    assert result.total_expense == Decimal("0.01070327")


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

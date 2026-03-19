from decimal import Decimal
from fbtc_taxgrinder.engine.compute import compute_period


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

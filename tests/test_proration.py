"""Tests for first-month proration and holding-mode behavior."""

from datetime import date
from decimal import Decimal

from fbtc_taxgrinder.engine.compute import HoldingMode, LotMonthInput, compute_lot_month
from fbtc_taxgrinder.models import Lot, MonthProceeds


def test_first_month_full_by_default():
    """Default: lot purchased Aug 19 uses full month (31 days)."""
    result = compute_lot_month(
        LotMonthInput(
            lot=Lot(
                id="lot-10",
                purchase_date=date(2024, 8, 19),
                original_shares=Decimal("1"),
                price_per_share=Decimal("51.3995"),
                total_cost=Decimal("51.3995"),
                btc_per_share_on_purchase=Decimal("0.00087437"),
                source_file="test.csv",
                events=[],
            ),
            year=2024,
            month=8,
            adj_btc=Decimal("0.00087437"),
            adj_basis=Decimal("51.3995"),
            shares=Decimal("1"),
            month_proceeds=MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        )
    )
    assert result.month_result.days_held == Decimal("31")
    assert result.month_result.days_in_month == Decimal("31")


def test_first_month_proration():
    """With prorate_first_month: lot purchased Aug 19, days_held = 31 - 19 = 12."""
    result = compute_lot_month(
        LotMonthInput(
            lot=Lot(
                id="lot-10",
                purchase_date=date(2024, 8, 19),
                original_shares=Decimal("1"),
                price_per_share=Decimal("51.3995"),
                total_cost=Decimal("51.3995"),
                btc_per_share_on_purchase=Decimal("0.00087437"),
                source_file="test.csv",
                events=[],
            ),
            year=2024,
            month=8,
            adj_btc=Decimal("0.00087437"),
            adj_basis=Decimal("51.3995"),
            shares=Decimal("1"),
            month_proceeds=MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        ),
        holding_mode=HoldingMode.PRORATE,
    )
    assert result.month_result.days_held == Decimal("12")
    assert result.month_result.days_in_month == Decimal("31")


def test_full_month_after_purchase():
    """Lot purchased Aug 19: September is a full month (30 days)."""
    result = compute_lot_month(
        LotMonthInput(
            lot=Lot(
                id="lot-10",
                purchase_date=date(2024, 8, 19),
                original_shares=Decimal("1"),
                price_per_share=Decimal("51.3995"),
                total_cost=Decimal("51.3995"),
                btc_per_share_on_purchase=Decimal("0.00087437"),
                source_file="test.csv",
                events=[],
            ),
            year=2024,
            month=9,
            adj_btc=Decimal("0.00087430"),
            adj_basis=Decimal("51.39"),
            shares=Decimal("1"),
            month_proceeds=MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01124247"),
            ),
        )
    )
    assert result.month_result.days_held == Decimal("30")


def test_lot_not_yet_active():
    """Lot purchased Sep 9: should skip August entirely."""
    result = compute_lot_month(
        LotMonthInput(
            lot=Lot(
                id="lot-12",
                purchase_date=date(2024, 9, 9),
                original_shares=Decimal("126"),
                price_per_share=Decimal("49.50"),
                total_cost=Decimal("6237.00"),
                btc_per_share_on_purchase=Decimal("0.00087425"),
                source_file="test.csv",
                events=[],
            ),
            year=2024,
            month=8,
            adj_btc=Decimal("0.11015550"),
            adj_basis=Decimal("6237.00"),
            shares=Decimal("126"),
            month_proceeds=MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        )
    )
    assert result is None  # Not active this month


def test_purchased_first_of_month():
    """Lot purchased Oct 1: default uses full month (31 days)."""
    result = compute_lot_month(
        LotMonthInput(
            lot=Lot(
                id="lot-x",
                purchase_date=date(2024, 10, 1),
                original_shares=Decimal("10"),
                price_per_share=Decimal("50.00"),
                total_cost=Decimal("500.00"),
                btc_per_share_on_purchase=Decimal("0.00087401"),
                source_file="test.csv",
                events=[],
            ),
            year=2024,
            month=10,
            adj_btc=Decimal("0.0087401"),
            adj_basis=Decimal("500.00"),
            shares=Decimal("10"),
            month_proceeds=MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01236501"),
            ),
        )
    )
    assert result is not None
    assert result.month_result.days_held == Decimal("31")
    assert result.month_result.days_in_month == Decimal("31")


def test_february_leap_year():
    """Lot active in Feb 2024 (leap year): days_in_month = 29."""
    result = compute_lot_month(
        LotMonthInput(
            lot=Lot(
                id="lot-x",
                purchase_date=date(2024, 1, 15),
                original_shares=Decimal("10"),
                price_per_share=Decimal("50.00"),
                total_cost=Decimal("500.00"),
                btc_per_share_on_purchase=Decimal("0.00087448"),
                source_file="test.csv",
                events=[],
            ),
            year=2024,
            month=2,
            adj_btc=Decimal("0.0087448"),
            adj_basis=Decimal("500.00"),
            shares=Decimal("10"),
            month_proceeds=MonthProceeds(
                btc_sold_per_share=Decimal("0"),
                proceeds_per_share_usd=Decimal("0"),
            ),
        )
    )
    assert result is not None
    assert result.month_result.days_in_month == Decimal("29")
    assert result.month_result.days_held == Decimal(
        "29"
    )  # Full month (purchased prior month)


def test_purchased_last_day_of_month_default():
    """Default: lot purchased Aug 31 uses full month (31 days)."""
    result = compute_lot_month(
        LotMonthInput(
            lot=Lot(
                id="lot-x",
                purchase_date=date(2024, 8, 31),
                original_shares=Decimal("10"),
                price_per_share=Decimal("50.00"),
                total_cost=Decimal("500.00"),
                btc_per_share_on_purchase=Decimal("0.00087430"),
                source_file="test.csv",
                events=[],
            ),
            year=2024,
            month=8,
            adj_btc=Decimal("0.0087430"),
            adj_basis=Decimal("500.00"),
            shares=Decimal("10"),
            month_proceeds=MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        )
    )
    assert result is not None
    assert result.month_result.days_held == Decimal("31")


def test_purchased_last_day_of_month_prorated():
    """With prorate_first_month: purchased Aug 31, days_held = 0, skip."""
    result = compute_lot_month(
        LotMonthInput(
            lot=Lot(
                id="lot-x",
                purchase_date=date(2024, 8, 31),
                original_shares=Decimal("10"),
                price_per_share=Decimal("50.00"),
                total_cost=Decimal("500.00"),
                btc_per_share_on_purchase=Decimal("0.00087430"),
                source_file="test.csv",
                events=[],
            ),
            year=2024,
            month=8,
            adj_btc=Decimal("0.0087430"),
            adj_basis=Decimal("500.00"),
            shares=Decimal("10"),
            month_proceeds=MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        ),
        holding_mode=HoldingMode.PRORATE,
    )
    assert result is None  # days_held = 0, not active

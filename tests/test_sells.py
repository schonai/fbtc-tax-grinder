from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import Lot, LotEvent, MonthProceeds
from fbtc_taxgrinder.engine.compute import compute_lot_month, LotMonthInput


def test_sell_mid_month():
    """Sell 14 of 204 shares on Dec 23. Month split into 3 phases."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell", date=date(2025, 12, 23),
                shares=Decimal("14"), price_per_share=Decimal("76.2201"),
                proceeds=Decimal("1067.08"), disposition_id="lot-1-sell-1",
            ),
        ],
    )
    result = compute_lot_month(LotMonthInput(
        lot=lot, year=2025, month=12,
        adj_btc=Decimal("0.17800000"),
        adj_basis=Decimal("7080.00"),
        shares=Decimal("204"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01581176"),
        ),
    ))
    assert result is not None
    # Should have one disposition
    assert len(result.dispositions) == 1
    d = result.dispositions[0]
    assert d.shares_sold == Decimal("14")
    assert d.lot_id == "lot-1"
    # Post-sell shares should be 190
    assert result.new_state.shares == Decimal("190")


def test_sell_full_liquidation():
    """Sell all shares — Phase 3 skipped."""
    lot = Lot(
        id="lot-x", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("10"), price_per_share=Decimal("50.00"),
        total_cost=Decimal("500.00"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell", date=date(2024, 10, 15),
                shares=Decimal("10"), price_per_share=Decimal("60.00"),
                proceeds=Decimal("600.00"), disposition_id="lot-x-sell-1",
            ),
        ],
    )
    result = compute_lot_month(LotMonthInput(
        lot=lot, year=2024, month=10,
        adj_btc=Decimal("0.00874000"),
        adj_basis=Decimal("499.50"),
        shares=Decimal("10"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01236501"),
        ),
    ))
    assert result is not None
    assert len(result.dispositions) == 1
    assert result.new_state.shares == Decimal("0")


def test_two_sells_same_month():
    """Two sells in the same month: expense -> dispose -> expense -> dispose -> expense."""
    lot = Lot(
        id="lot-x", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("100"), price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell", date=date(2025, 3, 10),
                shares=Decimal("20"), price_per_share=Decimal("60.00"),
                proceeds=Decimal("1200.00"), disposition_id="lot-x-sell-1",
            ),
            LotEvent(
                type="sell", date=date(2025, 3, 20),
                shares=Decimal("30"), price_per_share=Decimal("65.00"),
                proceeds=Decimal("1950.00"), disposition_id="lot-x-sell-2",
            ),
        ],
    )
    result = compute_lot_month(LotMonthInput(
        lot=lot, year=2025, month=3,
        adj_btc=Decimal("0.08700000"),
        adj_basis=Decimal("4950.00"),
        shares=Decimal("100"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01509769"),
        ),
    ))
    assert result is not None
    assert len(result.dispositions) == 2
    assert result.dispositions[0].shares_sold == Decimal("20")
    assert result.dispositions[1].shares_sold == Decimal("30")
    assert result.new_state.shares == Decimal("50")


def test_no_sell_event_normal_month():
    """Normal month with no sell — no dispositions."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv", events=[],
    )
    result = compute_lot_month(LotMonthInput(
        lot=lot, year=2024, month=8,
        adj_btc=Decimal("0.17839392"),
        adj_basis=Decimal("7101.24"),
        shares=Decimal("204"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01070327"),
        ),
    ))
    assert result is not None
    assert len(result.dispositions) == 0

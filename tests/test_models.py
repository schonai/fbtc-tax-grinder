from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import (
    Lot, LotEvent, LotState, ExpenseResult, Disposition,
    YearResult, MonthProceeds, YearProceeds,
)


def test_lot_total_cost():
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[],
    )
    assert lot.total_cost == Decimal("7101.24")
    assert lot.id == "lot-1"


def test_lot_shares_at_date_no_events():
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[],
    )
    assert lot.shares_at_date(date(2024, 6, 1)) == Decimal("204")


def test_lot_shares_at_date_after_sell():
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell",
                date=date(2025, 12, 23),
                shares=Decimal("14"),
                price_per_share=Decimal("76.2201"),
                proceeds=Decimal("1067.08"),
                disposition_id="lot-1-sell-1",
            ),
        ],
    )
    assert lot.shares_at_date(date(2025, 12, 22)) == Decimal("204")
    assert lot.shares_at_date(date(2025, 12, 23)) == Decimal("190")
    assert lot.shares_at_date(date(2026, 1, 1)) == Decimal("190")


def test_lot_state_roundtrip():
    state = LotState(
        adj_btc=Decimal("0.17821032"),
        adj_basis=Decimal("7093.928514"),
        shares=Decimal("204"),
    )
    assert state.adj_btc == Decimal("0.17821032")


def test_month_proceeds():
    mp = MonthProceeds(
        btc_sold_per_share=Decimal("0.00000018"),
        proceeds_per_share_usd=Decimal("0.01070327"),
    )
    assert mp.btc_sold_per_share == Decimal("0.00000018")


def test_lot_shares_at_date_multiple_sells():
    """Multiple sell events should cumulatively reduce shares."""
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("100"),
        price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell", date=date(2025, 3, 10),
                shares=Decimal("20"), price_per_share=Decimal("60.00"),
                proceeds=Decimal("1200.00"), disposition_id="sell-1",
            ),
            LotEvent(
                type="sell", date=date(2025, 6, 15),
                shares=Decimal("30"), price_per_share=Decimal("65.00"),
                proceeds=Decimal("1950.00"), disposition_id="sell-2",
            ),
        ],
    )
    assert lot.shares_at_date(date(2025, 3, 9)) == Decimal("100")
    assert lot.shares_at_date(date(2025, 3, 10)) == Decimal("80")
    assert lot.shares_at_date(date(2025, 6, 14)) == Decimal("80")
    assert lot.shares_at_date(date(2025, 6, 15)) == Decimal("50")
    assert lot.shares_at_date(date(2026, 1, 1)) == Decimal("50")

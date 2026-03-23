"""Tests for JSON codec encode/decode round-trips."""

from datetime import date
from decimal import Decimal

from fbtc_taxgrinder.db.codec import _reconstruct, decode, encode
from fbtc_taxgrinder.models import (
    Disposition,
    Lot,
    LotEvent,
    LotState,
    MonthProceeds,
    ExpenseResult,
    YearProceeds,
    YearResult,
)


def test_lot_roundtrip():
    """Lot with events survives encode/decode round-trip."""
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
    text = encode([lot])
    loaded = decode(list[Lot], text)
    assert len(loaded) == 1
    assert loaded[0].id == "lot-1"
    assert loaded[0].original_shares == Decimal("204")
    assert loaded[0].btc_per_share_on_purchase == Decimal("0.00087448")
    assert len(loaded[0].events) == 1
    assert loaded[0].events[0].shares == Decimal("14")
    assert loaded[0].events[0].date == date(2025, 12, 23)


def test_year_proceeds_roundtrip():
    """YearProceeds with daily and monthly data round-trips correctly."""
    yp = YearProceeds(
        daily={date(2024, 1, 11): Decimal("0.00087448")},
        monthly={
            date(2024, 8, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        },
        source="test.pdf",
    )
    text = encode(yp)
    loaded = decode(YearProceeds, text)
    assert loaded.daily[date(2024, 1, 11)] == Decimal("0.00087448")
    assert loaded.monthly[date(2024, 8, 31)].btc_sold_per_share == Decimal("0.00000018")
    assert loaded.source == "test.pdf"


def test_lot_state_dict_roundtrip():
    """Dict of LotState values round-trips correctly."""
    states = {
        "lot-1": LotState(
            adj_btc=Decimal("0.17821032"),
            adj_basis=Decimal("7093.928514"),
            shares=Decimal("204"),
        ),
    }
    text = encode(states)
    loaded = decode(dict[str, LotState], text)
    assert loaded["lot-1"].adj_btc == Decimal("0.17821032")
    assert loaded["lot-1"].shares == Decimal("204")


def test_year_result_roundtrip():
    """YearResult with dispositions and end_states round-trips correctly."""
    yr = YearResult(
        year=2024,
        lot_results={
            "lot-1": [
                ExpenseResult(
                    sell_date=date(2024, 8, 31),
                    days_held=Decimal("31"),
                    days_in_month=Decimal("31"),
                    shares=Decimal("204"),
                    total_btc_sold=Decimal("0.00003672"),
                    cost_basis_of_sold=Decimal("1.461695179"),
                    total_expense=Decimal("2.18346708"),
                    gain_loss=Decimal("0.7217719012"),
                    adj_btc=Decimal("0.17835720"),
                    adj_basis=Decimal("7099.778305"),
                ),
            ],
        },
        dispositions=[
            Disposition(
                lot_id="lot-1",
                disposition_id="lot-1-sell-1",
                date_sold=date(2025, 12, 23),
                shares_sold=Decimal("14"),
                proceeds=Decimal("1067.08"),
                disposed_btc=Decimal("0.00012"),
                disposed_basis=Decimal("5.00"),
                gain_loss=Decimal("1062.08"),
            ),
        ],
        end_states={
            "lot-1": LotState(
                adj_btc=Decimal("0.17800000"),
                adj_basis=Decimal("7090.00"),
                shares=Decimal("190"),
            ),
        },
        total_investment_expense=Decimal("2.18346708"),
        total_reportable_gain=Decimal("0.7217719012"),
        total_cost_basis_of_expense=Decimal("1.461695179"),
    )
    text = encode(yr)
    loaded = decode(YearResult, text)
    assert loaded.year == 2024
    assert loaded.lot_results["lot-1"][0].adj_btc == Decimal("0.17835720")
    assert len(loaded.dispositions) == 1
    assert loaded.dispositions[0].date_sold == date(2025, 12, 23)
    assert loaded.dispositions[0].proceeds == Decimal("1067.08")
    assert loaded.end_states["lot-1"].shares == Decimal("190")


def test_empty_list():
    """Empty list round-trips to empty list."""
    text = encode([])
    loaded = decode(list[Lot], text)
    assert loaded == []


def test_plain_values_passthrough():
    """Plain int and str decode as-is."""
    assert decode(int, "42") == 42
    assert decode(str, '"hello"') == "hello"


def test_decode_none():
    """_reconstruct returns None when data is None."""
    assert _reconstruct(Decimal, None) is None


def test_encode_no_scientific_notation():
    """Small-exponent Decimals must serialize as fixed-point, not scientific."""
    yp = YearProceeds(
        daily={},
        monthly={
            date(2024, 8, 31): MonthProceeds(
                btc_sold_per_share=Decimal("1.8E-7"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        },
        source="test.pdf",
    )
    text = encode(yp)
    assert "E-" not in text and "e-" not in text
    assert "0.00000018" in text


def test_reconstruct_unknown_type_fallback():
    """_reconstruct returns data as-is for unknown/unhandled types."""
    # float is not handled by any branch — should fall through to `return data`
    assert _reconstruct(float, 3.14) == 3.14
    assert _reconstruct(bool, True) is True


def test_lot_without_events_roundtrip():
    """Lot with empty events list round-trips correctly."""
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("10"),
        price_per_share=Decimal("50.00"),
        total_cost=Decimal("500.00"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[],
    )
    text = encode(lot)
    loaded = decode(Lot, text)
    assert loaded.events == []
    assert loaded.id == "lot-1"

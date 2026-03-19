from datetime import date
from decimal import Decimal

from fbtc_taxgrinder.db.codec import decode, encode
from fbtc_taxgrinder.models import (
    Disposition, Lot, LotEvent, LotState, MonthProceeds, MonthResult,
    YearProceeds, YearResult,
)


def test_lot_roundtrip():
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
    yr = YearResult(
        year=2024,
        lot_results={
            "lot-1": [
                MonthResult(
                    month=8, days_held=Decimal("31"), days_in_month=Decimal("31"),
                    shares=Decimal("204"), total_btc_sold=Decimal("0.00003672"),
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
    text = encode([])
    loaded = decode(list[Lot], text)
    assert loaded == []


def test_plain_values_passthrough():
    assert decode(int, "42") == 42
    assert decode(str, '"hello"') == "hello"

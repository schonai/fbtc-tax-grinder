from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import (
    Lot, LotEvent, LotState, MonthResult, Disposition,
    YearResult, MonthProceeds, YearProceeds,
)
from fbtc_taxgrinder.db import lots, proceeds, results, state


def test_lots_roundtrip(data_dir):
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
    lots.save(data_dir, [lot])
    loaded = lots.load(data_dir)
    assert len(loaded) == 1
    assert loaded[0].id == "lot-1"
    assert loaded[0].original_shares == Decimal("204")
    assert loaded[0].btc_per_share_on_purchase == Decimal("0.00087448")
    assert len(loaded[0].events) == 1
    assert loaded[0].events[0].shares == Decimal("14")


def test_lots_load_empty(data_dir):
    loaded = lots.load(data_dir)
    assert loaded == []


def test_proceeds_roundtrip(data_dir):
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
    proceeds.save(data_dir, 2024, yp)
    loaded = proceeds.load(data_dir, 2024)
    assert loaded is not None
    assert loaded.daily[date(2024, 1, 11)] == Decimal("0.00087448")
    assert loaded.monthly[date(2024, 8, 31)].btc_sold_per_share == Decimal("0.00000018")


def test_proceeds_load_missing(data_dir):
    loaded = proceeds.load(data_dir, 2024)
    assert loaded is None


def test_state_roundtrip(data_dir):
    states = {
        "lot-1": LotState(
            adj_btc=Decimal("0.17821032"),
            adj_basis=Decimal("7093.928514"),
            shares=Decimal("204"),
        ),
    }
    state.save(data_dir, 2024, states)
    loaded = state.load(data_dir, 2024)
    assert loaded is not None
    assert loaded["lot-1"].adj_btc == Decimal("0.17821032")


def test_state_load_missing(data_dir):
    loaded = state.load(data_dir, 2024)
    assert loaded is None


def test_results_roundtrip(data_dir):
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
        dispositions=[],
        end_states={},
        total_investment_expense=Decimal("2.18346708"),
        total_reportable_gain=Decimal("0.7217719012"),
        total_cost_basis_of_expense=Decimal("1.461695179"),
    )
    results.save(data_dir, yr)
    loaded = results.load(data_dir, 2024)
    assert loaded is not None
    assert loaded.year == 2024
    assert len(loaded.lot_results["lot-1"]) == 1
    assert loaded.lot_results["lot-1"][0].adj_btc == Decimal("0.17835720")

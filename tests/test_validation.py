"""Cross-reference engine output against known 2024 spreadsheet values.

Lots 1-9 are unaffected by the proration bug (all purchased before Aug 2024,
so their first active month is Aug with a full 31 days).

Lots 10-15 are affected by the bug — the engine's correct proration will
produce different values from the spreadsheet.
"""
from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import (
    Lot, MonthProceeds, YearProceeds,
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

LOTS_2024 = [
    Lot(id="lot-1", purchase_date=date(2024, 1, 25), original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"), total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"), source_file="t", events=[]),
    Lot(id="lot-2", purchase_date=date(2024, 2, 17), original_shares=Decimal("2"),
        price_per_share=Decimal("45.81"), total_cost=Decimal("91.62"),
        btc_per_share_on_purchase=Decimal("0.00087448"), source_file="t", events=[]),
    Lot(id="lot-3", purchase_date=date(2024, 2, 23), original_shares=Decimal("9"),
        price_per_share=Decimal("44.85"), total_cost=Decimal("403.65"),
        btc_per_share_on_purchase=Decimal("0.00087448"), source_file="t", events=[]),
    Lot(id="lot-4", purchase_date=date(2024, 3, 6), original_shares=Decimal("42"),
        price_per_share=Decimal("58.315"), total_cost=Decimal("2449.23"),
        btc_per_share_on_purchase=Decimal("0.00087448"), source_file="t", events=[]),
    Lot(id="lot-5", purchase_date=date(2024, 3, 19), original_shares=Decimal("1"),
        price_per_share=Decimal("56.639"), total_cost=Decimal("56.639"),
        btc_per_share_on_purchase=Decimal("0.00087448"), source_file="t", events=[]),
    Lot(id="lot-6", purchase_date=date(2024, 3, 22), original_shares=Decimal("1"),
        price_per_share=Decimal("56.18"), total_cost=Decimal("56.18"),
        btc_per_share_on_purchase=Decimal("0.00087448"), source_file="t", events=[]),
    Lot(id="lot-7", purchase_date=date(2024, 4, 18), original_shares=Decimal("1"),
        price_per_share=Decimal("55.82"), total_cost=Decimal("55.82"),
        btc_per_share_on_purchase=Decimal("0.00087448"), source_file="t", events=[]),
    Lot(id="lot-8", purchase_date=date(2024, 4, 18), original_shares=Decimal("54"),
        price_per_share=Decimal("55.6097"), total_cost=Decimal("3002.9238"),
        btc_per_share_on_purchase=Decimal("0.00087448"), source_file="t", events=[]),
    Lot(id="lot-9", purchase_date=date(2024, 6, 5), original_shares=Decimal("4"),
        price_per_share=Decimal("62.2379"), total_cost=Decimal("248.9516"),
        btc_per_share_on_purchase=Decimal("0.00087448"), source_file="t", events=[]),
]

# Expected EOY values from spreadsheet (lots 1-9 are bug-free)
EXPECTED_EOY = {
    "lot-1": {"adj_btc": Decimal("0.17821032"), "adj_basis": Decimal("7093.928514")},
    "lot-2": {"adj_btc": Decimal("0.00174716"), "adj_basis": Decimal("91.52566741")},
    "lot-3": {"adj_btc": Decimal("0.00786222"), "adj_basis": Decimal("403.2343991")},
    "lot-4": {"adj_btc": Decimal("0.03669036"), "adj_basis": Decimal("2446.708256")},
    "lot-5": {"adj_btc": Decimal("0.00087358"), "adj_basis": Decimal("56.58068409")},
    "lot-6": {"adj_btc": Decimal("0.00087358"), "adj_basis": Decimal("56.12215668")},
    "lot-7": {"adj_btc": Decimal("0.00087358"), "adj_basis": Decimal("55.76252734")},
    "lot-8": {"adj_btc": Decimal("0.04717332"), "adj_basis": Decimal("2999.831969")},
    "lot-9": {"adj_btc": Decimal("0.00349432"), "adj_basis": Decimal("248.6952777")},
}


def test_lots_1_through_9_match_spreadsheet():
    """Lots 1-9: purchased before Aug, full-month proration, should match spreadsheet exactly."""
    result = compute_year(
        lots=LOTS_2024,
        proceeds=PROCEEDS_2024,
        prior_state=None,
        year=2024,
    )

    for lot_id, expected in EXPECTED_EOY.items():
        lot_months = result.lot_results[lot_id]
        assert lot_months, f"No results for {lot_id}"
        last_month = lot_months[-1]

        # Compare with tight tolerance — Decimal arithmetic should be near-exact
        btc_diff = abs(last_month.adj_btc - expected["adj_btc"])
        basis_diff = abs(last_month.adj_basis - expected["adj_basis"])

        assert btc_diff < Decimal("1E-8"), (
            f"{lot_id} adj_btc: expected {expected['adj_btc']}, "
            f"got {last_month.adj_btc}, diff={btc_diff}"
        )
        # Spreadsheet uses float arithmetic with intermediate rounding;
        # engine uses full Decimal precision. Allow 0.01 tolerance.
        assert basis_diff < Decimal("0.01"), (
            f"{lot_id} adj_basis: expected {expected['adj_basis']}, "
            f"got {last_month.adj_basis}, diff={basis_diff}"
        )


LOTS_10_TO_15 = [
    Lot(id="lot-10", purchase_date=date(2024, 8, 19), original_shares=Decimal("1"),
        price_per_share=Decimal("51.3995"), total_cost=Decimal("51.3995"),
        btc_per_share_on_purchase=Decimal("0.00087437"), source_file="t", events=[]),
    Lot(id="lot-11", purchase_date=date(2024, 8, 19), original_shares=Decimal("5"),
        price_per_share=Decimal("51.3669"), total_cost=Decimal("256.8345"),
        btc_per_share_on_purchase=Decimal("0.00087437"), source_file="t", events=[]),
    Lot(id="lot-12", purchase_date=date(2024, 9, 9), original_shares=Decimal("126"),
        price_per_share=Decimal("49.50"), total_cost=Decimal("6237.00"),
        btc_per_share_on_purchase=Decimal("0.00087425"), source_file="t", events=[]),
    Lot(id="lot-13", purchase_date=date(2024, 9, 9), original_shares=Decimal("86"),
        price_per_share=Decimal("49.4297"), total_cost=Decimal("4250.9542"),
        btc_per_share_on_purchase=Decimal("0.00087425"), source_file="t", events=[]),
    Lot(id="lot-14", purchase_date=date(2024, 10, 17), original_shares=Decimal("82"),
        price_per_share=Decimal("58.62"), total_cost=Decimal("4806.84"),
        btc_per_share_on_purchase=Decimal("0.00087401"), source_file="t", events=[]),
    Lot(id="lot-15", purchase_date=date(2024, 11, 5), original_shares=Decimal("17"),
        price_per_share=Decimal("61.2986"), total_cost=Decimal("1042.0762"),
        btc_per_share_on_purchase=Decimal("0.00087391"), source_file="t", events=[]),
]

# Spreadsheet values (with proration bug — full month instead of prorated)
BUGGY_EOY_10_TO_15 = {
    "lot-10": {"adj_btc": Decimal("0.00087347"), "adj_basis": Decimal("51.34657205")},
    "lot-11": {"adj_btc": Decimal("0.00436735"), "adj_basis": Decimal("256.5700281")},
    "lot-12": {"adj_btc": Decimal("0.11006478"), "adj_basis": Decimal("6231.86185")},
    "lot-13": {"adj_btc": Decimal("0.07512358"), "adj_basis": Decimal("4247.452189")},
    "lot-14": {"adj_btc": Decimal("0.07162454"), "adj_basis": Decimal("4803.869521")},
    "lot-15": {"adj_btc": Decimal("0.01485035"), "adj_basis": Decimal("1041.646881")},
}


def test_lots_10_through_15_differ_from_buggy_spreadsheet():
    """Lots 10-15: correct proration should produce DIFFERENT values from buggy spreadsheet."""
    all_lots = LOTS_2024 + LOTS_10_TO_15
    result = compute_year(
        lots=all_lots,
        proceeds=PROCEEDS_2024,
        prior_state=None,
        year=2024,
    )

    for lot_id, buggy in BUGGY_EOY_10_TO_15.items():
        lot_months = result.lot_results[lot_id]
        assert lot_months, f"No results for {lot_id}"
        last_month = lot_months[-1]

        # Values should differ from the buggy spreadsheet
        # (correct proration reduces first-month activity)
        btc_diff = abs(last_month.adj_btc - buggy["adj_btc"])
        assert btc_diff > Decimal("1E-12"), (
            f"{lot_id} adj_btc matches buggy spreadsheet — proration fix may not be working"
        )

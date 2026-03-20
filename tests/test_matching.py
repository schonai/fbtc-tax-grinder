from datetime import date
from decimal import Decimal

import pytest

from fbtc_taxgrinder.engine.matching import match_sell_to_lot
from fbtc_taxgrinder.models import Lot


def _make_lot(lot_id: str, shares: str, purchase_date: date = date(2024, 1, 25)) -> Lot:
    return Lot(
        id=lot_id,
        purchase_date=purchase_date,
        original_shares=Decimal(shares),
        price_per_share=Decimal("50.00"),
        total_cost=Decimal(shares) * Decimal("50.00"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[],
    )


def test_unique_match():
    lots = [_make_lot("lot-1", "100"), _make_lot("lot-2", "50")]
    matched = match_sell_to_lot(
        lots, sell_shares=Decimal("80"), sell_date=date(2024, 12, 1)
    )
    assert matched.id == "lot-1"


def test_ambiguous_match():
    lots = [_make_lot("lot-1", "100"), _make_lot("lot-2", "100")]
    with pytest.raises(ValueError, match="Ambiguous"):
        match_sell_to_lot(lots, sell_shares=Decimal("50"), sell_date=date(2024, 12, 1))


def test_no_match():
    lots = [_make_lot("lot-1", "10")]
    with pytest.raises(ValueError, match="No lot"):
        match_sell_to_lot(lots, sell_shares=Decimal("50"), sell_date=date(2024, 12, 1))


def test_exact_match_among_multiple():
    """If sell_shares exactly equals one lot's remaining shares, it's unambiguous."""
    lots = [_make_lot("lot-1", "100"), _make_lot("lot-2", "50")]
    matched = match_sell_to_lot(
        lots, sell_shares=Decimal("50"), sell_date=date(2024, 12, 1)
    )
    assert matched.id == "lot-2"

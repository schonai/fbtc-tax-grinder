from __future__ import annotations

from datetime import date
from decimal import Decimal

from fbtc_taxgrinder.models import Lot


def match_sell_to_lot(
    lots: list[Lot],
    *,
    sell_shares: Decimal,
    sell_date: date,
) -> Lot:
    """Match a sell transaction to a lot. Raises ValueError if ambiguous or no match."""
    candidates = [
        lot for lot in lots
        if lot.shares_at_date(sell_date) >= sell_shares
        and lot.purchase_date < sell_date
    ]

    if not candidates:
        raise ValueError(
            f"No lot found with >= {sell_shares} remaining shares on {sell_date.isoformat()}"
        )

    if len(candidates) == 1:
        return candidates[0]

    # Check for exact match (sell_shares == remaining shares)
    exact = [
        lot for lot in candidates
        if lot.shares_at_date(sell_date) == sell_shares
    ]
    if len(exact) == 1:
        return exact[0]

    lot_info = ", ".join(
        f"{lot.id} ({lot.shares_at_date(sell_date)} shares, purchased {lot.purchase_date})"
        for lot in candidates
    )
    raise ValueError(
        f"Ambiguous sell: {sell_shares} shares on {sell_date.isoformat()} "
        f"matches multiple lots: {lot_info}"
    )

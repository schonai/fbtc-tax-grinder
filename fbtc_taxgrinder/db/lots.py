from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from fbtc_taxgrinder.models import Lot, LotEvent


def _lot_to_dict(lot: Lot) -> dict:
    return {
        "id": lot.id,
        "purchase_date": lot.purchase_date.isoformat(),
        "original_shares": str(lot.original_shares),
        "price_per_share": str(lot.price_per_share),
        "total_cost": str(lot.total_cost),
        "btc_per_share_on_purchase": str(lot.btc_per_share_on_purchase),
        "source_file": lot.source_file,
        "events": [
            {
                "type": e.type,
                "date": e.date.isoformat(),
                "shares": str(e.shares),
                "price_per_share": str(e.price_per_share),
                "proceeds": str(e.proceeds),
                "disposition_id": e.disposition_id,
            }
            for e in lot.events
        ],
    }


def _dict_to_lot(d: dict) -> Lot:
    return Lot(
        id=d["id"],
        purchase_date=date.fromisoformat(d["purchase_date"]),
        original_shares=Decimal(d["original_shares"]),
        price_per_share=Decimal(d["price_per_share"]),
        total_cost=Decimal(d["total_cost"]),
        btc_per_share_on_purchase=Decimal(d["btc_per_share_on_purchase"]),
        source_file=d["source_file"],
        events=[
            LotEvent(
                type=e["type"],
                date=date.fromisoformat(e["date"]),
                shares=Decimal(e["shares"]),
                price_per_share=Decimal(e["price_per_share"]),
                proceeds=Decimal(e["proceeds"]),
                disposition_id=e["disposition_id"],
            )
            for e in d.get("events", [])
        ],
    )


def save(data_dir: Path, lot_list: list[Lot]) -> None:
    path = data_dir / "lots.json"
    with open(path, "w") as f:
        json.dump([_lot_to_dict(lot) for lot in lot_list], f, indent=2)


def load(data_dir: Path) -> list[Lot]:
    path = data_dir / "lots.json"
    if not path.exists():
        return []
    with open(path) as f:
        return [_dict_to_lot(d) for d in json.load(f)]

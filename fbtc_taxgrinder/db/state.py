from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from fbtc_taxgrinder.models import LotState


def save(data_dir: Path, year: int, states: dict[str, LotState]) -> None:
    path = data_dir / "state" / f"{year}.json"
    data = {
        lot_id: {
            "adj_btc": str(s.adj_btc),
            "adj_basis": str(s.adj_basis),
            "shares": str(s.shares),
        }
        for lot_id, s in states.items()
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load(data_dir: Path, year: int) -> dict[str, LotState] | None:
    path = data_dir / "state" / f"{year}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    return {
        lot_id: LotState(
            adj_btc=Decimal(v["adj_btc"]),
            adj_basis=Decimal(v["adj_basis"]),
            shares=Decimal(v["shares"]),
        )
        for lot_id, v in data.items()
    }

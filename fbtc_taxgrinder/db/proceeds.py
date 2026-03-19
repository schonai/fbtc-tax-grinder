from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from fbtc_taxgrinder.models import MonthProceeds, YearProceeds


def save(data_dir: Path, year: int, yp: YearProceeds) -> None:
    path = data_dir / "proceeds" / f"{year}.json"
    data = {
        "daily": {
            d.isoformat(): {"btc_per_share": str(v)}
            for d, v in yp.daily.items()
        },
        "monthly": {
            d.isoformat(): {
                "btc_sold_per_share": str(mp.btc_sold_per_share),
                "proceeds_per_share_usd": str(mp.proceeds_per_share_usd),
            }
            for d, mp in yp.monthly.items()
        },
        "source": yp.source,
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load(data_dir: Path, year: int) -> YearProceeds | None:
    path = data_dir / "proceeds" / f"{year}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    daily = {
        date.fromisoformat(k): Decimal(v["btc_per_share"])
        for k, v in data["daily"].items()
    }
    monthly = {
        date.fromisoformat(k): MonthProceeds(
            btc_sold_per_share=Decimal(v["btc_sold_per_share"]),
            proceeds_per_share_usd=Decimal(v["proceeds_per_share_usd"]),
        )
        for k, v in data["monthly"].items()
    }
    return YearProceeds(daily=daily, monthly=monthly, source=data["source"])

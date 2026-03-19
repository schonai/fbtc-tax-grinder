from __future__ import annotations

from pathlib import Path

from fbtc_taxgrinder.db.codec import decode, encode
from fbtc_taxgrinder.models import Lot


def save(data_dir: Path, lot_list: list[Lot]) -> None:
    """Save lots to data_dir/lots.json."""
    (data_dir / "lots.json").write_text(encode(lot_list))


def load(data_dir: Path) -> list[Lot]:
    """Load lots from data_dir/lots.json, returning [] if missing."""
    path = data_dir / "lots.json"
    if not path.exists():
        return []
    return decode(list[Lot], path.read_text())

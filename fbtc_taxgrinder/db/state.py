from __future__ import annotations

from pathlib import Path

from fbtc_taxgrinder.db.codec import decode, encode
from fbtc_taxgrinder.models import LotState


def save(data_dir: Path, year: int, states: dict[str, LotState]) -> None:
    """Save lot states to data_dir/state/{year}.json."""
    (data_dir / "state" / f"{year}.json").write_text(encode(states))


def load(data_dir: Path, year: int) -> dict[str, LotState] | None:
    """Load lot states, returning None if missing."""
    path = data_dir / "state" / f"{year}.json"
    if not path.exists():
        return None
    return decode(dict[str, LotState], path.read_text())

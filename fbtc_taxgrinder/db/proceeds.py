"""Persistence layer for yearly proceeds data."""
from __future__ import annotations

from pathlib import Path

from fbtc_taxgrinder.db.codec import decode, encode
from fbtc_taxgrinder.models import YearProceeds


def save(data_dir: Path, year: int, yp: YearProceeds) -> None:
    """Save year proceeds to data_dir/proceeds/{year}.json."""
    (data_dir / "proceeds" / f"{year}.json").write_text(encode(yp))


def load(data_dir: Path, year: int) -> YearProceeds | None:
    """Load year proceeds, returning None if missing."""
    path = data_dir / "proceeds" / f"{year}.json"
    if not path.exists():
        return None
    return decode(YearProceeds, path.read_text())

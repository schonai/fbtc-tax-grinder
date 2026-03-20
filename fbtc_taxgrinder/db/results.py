"""Persistence layer for computed year results."""

from __future__ import annotations

from pathlib import Path

from fbtc_taxgrinder.db.codec import decode, encode
from fbtc_taxgrinder.models import YearResult


def save(data_dir: Path, yr: YearResult) -> None:
    """Save year results to data_dir/results/{year}.json."""
    (data_dir / "results" / f"{yr.year}.json").write_text(encode(yr))


def load(data_dir: Path, year: int) -> YearResult | None:
    """Load year results, returning None if missing."""
    path = data_dir / "results" / f"{year}.json"
    if not path.exists():
        return None
    return decode(YearResult, path.read_text())

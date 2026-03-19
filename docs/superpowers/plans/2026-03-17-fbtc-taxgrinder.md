# fbtc-taxgrinder Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Status (2026-03-19):** Tasks 1-5 complete (54 tests, 97% coverage). Next: Task 6 (compute_year).
| Task | Status | Coverage |
|------|--------|----------|
| 1. Project Scaffolding | ✅ | — |
| 2. Data Models | ✅ | 100% |
| 3. JSON Data Access Layer | ✅ | 96% |
| 4. Core Engine — Single Period | ✅ | 99% |
| 5. Engine — Monthly + Sells | ✅ | 99% |
| 6-14 | Not started | — |

**Goal:** Build a Python CLI tool that computes IRS-reportable FBTC tax lots using Fidelity's 6-step WHFIT method, replacing an error-prone Google Sheets implementation.

**Architecture:** Layered Python package — pure computation engine (no I/O), JSON data access layer, parsers for ETrade CSV and Fidelity PDF, Click CLI as thin glue. All arithmetic uses `Decimal`. Designed so a web UI can replace the CLI without touching engine/db layers.

**Tech Stack:** Python 3.12+, `click` (CLI), `pdfplumber` (PDF parsing), `pytest` + `pytest-cov` (testing), `Decimal` (arithmetic), JSON (persistence)

**Coverage Requirement:** Every task must achieve 90%+ test coverage on the files it creates or modifies. Run `pytest --cov=fbtc_taxgrinder --cov-report=term-missing` after each task to verify. Add tests for any uncovered branches before committing.

**Quality Standards:**
- All functions must have type annotations (parameters and return types)
- All public functions must have docstrings explaining purpose, args, and return values
- No `# type: ignore` or `noqa` without a comment explaining why
- All Decimal values constructed from strings, never from floats
- No bare `except:` — always catch specific exceptions
- Imports sorted: stdlib, third-party, local (enforced by convention)
- No dead code, no commented-out code, no TODO without a linked issue

**Spec:** `docs/superpowers/specs/2026-03-17-fbtc-taxgrinder-design.md`

---

## File Structure

```
fbtc-taxgrinder/
├── fbtc_taxgrinder/
│   ├── __init__.py
│   ├── models.py              # Dataclasses: Lot, LotEvent, MonthResult, Disposition, YearResult, LotState, YearProceeds
│   ├── db/
│   │   ├── __init__.py
│   │   ├── lots.py            # Load/save data/lots.json
│   │   ├── proceeds.py        # Load/save data/proceeds/{year}.json
│   │   ├── results.py         # Load/save data/results/{year}.json
│   │   └── state.py           # Load/save data/state/{year}.json
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── compute.py         # compute_year(), compute_lot_month(), compute_period()
│   │   └── matching.py        # match_sell_to_lot()
│   ├── parsers/
│   │   ├── __init__.py
│   │   ├── etrade.py          # parse_etrade_csv() -> list of buy/sell transactions
│   │   └── fidelity_pdf.py    # parse_fidelity_pdf() -> YearProceeds
│   ├── export/
│   │   ├── __init__.py
│   │   └── csv_export.py      # export_year_csv()
│   └── cli/
│       ├── __init__.py
│       └── commands.py        # Click commands: import-proceeds, import-trades, compute, export, lots, status
├── data/                      # Created at runtime
├── tests/
│   ├── conftest.py            # Shared fixtures: sample lots, proceeds, tmp data dirs
│   ├── test_models.py
│   ├── test_compute.py        # Core engine: single month, multi-month chain, zero-expense months
│   ├── test_proration.py      # First-month days_held, edge cases
│   ├── test_sells.py          # Mid-month sell phases, full liquidation, multi-sell month
│   ├── test_matching.py       # Sell-to-lot matching: unique, ambiguous, none
│   ├── test_db.py             # JSON round-trip for all data types
│   ├── test_etrade_parser.py  # ETrade CSV parsing, FBTC filtering, idempotency
│   ├── test_fidelity_parser.py # PDF text parsing
│   ├── test_csv_export.py     # CSV output format
│   ├── test_cli.py            # CLI integration tests
│   └── test_validation.py     # Cross-reference with spreadsheet 2024 data
├── main.py
└── pyproject.toml
```

---

## Task 1: Project Scaffolding ✅

**Files:**
- Create: `pyproject.toml`
- Create: `main.py`
- Create: `fbtc_taxgrinder/__init__.py`
- Create: `fbtc_taxgrinder/db/__init__.py`
- Create: `fbtc_taxgrinder/engine/__init__.py`
- Create: `fbtc_taxgrinder/parsers/__init__.py`
- Create: `fbtc_taxgrinder/export/__init__.py`
- Create: `fbtc_taxgrinder/cli/__init__.py`

- [x] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.backends._legacy:_Backend"

[project]
name = "fbtc-taxgrinder"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "click>=8.0",
    "pdfplumber>=0.10",
    "requests>=2.31",
]

[project.scripts]
fbtc-taxgrinder = "fbtc_taxgrinder.cli.commands:cli"

[tool.pytest.ini_options]
testpaths = ["tests"]

[project.optional-dependencies]
dev = ["pytest>=7.0", "pytest-cov>=4.0"]
```

- [x] **Step 2: Create empty __init__.py files and main.py**

`main.py`:
```python
from fbtc_taxgrinder.cli.commands import cli

if __name__ == "__main__":
    cli()
```

`fbtc_taxgrinder/__init__.py`: empty
`fbtc_taxgrinder/db/__init__.py`: empty
`fbtc_taxgrinder/engine/__init__.py`: empty
`fbtc_taxgrinder/parsers/__init__.py`: empty
`fbtc_taxgrinder/export/__init__.py`: empty
`fbtc_taxgrinder/cli/__init__.py`: empty

- [x] **Step 3: Create minimal CLI placeholder**

`fbtc_taxgrinder/cli/commands.py`:
```python
import click


@click.group()
def cli():
    """FBTC Tax Lot Grinder — compute IRS-reportable WHFIT tax lots."""
    pass
```

- [x] **Step 4: Install in dev mode and verify**

Run: `pip install -e ".[dev]"`
Run: `fbtc-taxgrinder --help`
Expected: Shows help with no commands yet.

- [x] **Step 5: Commit**

```bash
git add pyproject.toml main.py fbtc_taxgrinder/
git commit -m "scaffold: project structure with click CLI entry point"
```

> **Deviations:** Fixed build-backend from `setuptools.backends._legacy:_Backend` (doesn't exist) to `setuptools.build_meta`. Added `.gitignore` and `.venv`.

---

## Task 2: Data Models ✅

**Files:**
- Create: `fbtc_taxgrinder/models.py`
- Create: `tests/test_models.py`

- [x] **Step 1: Write failing test for models**

`tests/test_models.py`:
```python
from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import (
    Lot, LotEvent, LotState, MonthResult, Disposition,
    YearResult, MonthProceeds, YearProceeds,
)


def test_lot_total_cost():
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[],
    )
    assert lot.total_cost == Decimal("7101.24")
    assert lot.id == "lot-1"


def test_lot_shares_at_date_no_events():
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[],
    )
    assert lot.shares_at_date(date(2024, 6, 1)) == Decimal("204")


def test_lot_shares_at_date_after_sell():
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell",
                date=date(2025, 12, 23),
                shares=Decimal("14"),
                price_per_share=Decimal("76.2201"),
                proceeds=Decimal("1067.08"),
                disposition_id="lot-1-sell-1",
            ),
        ],
    )
    assert lot.shares_at_date(date(2025, 12, 22)) == Decimal("204")
    assert lot.shares_at_date(date(2025, 12, 23)) == Decimal("190")
    assert lot.shares_at_date(date(2026, 1, 1)) == Decimal("190")


def test_lot_state_roundtrip():
    state = LotState(
        adj_btc=Decimal("0.17821032"),
        adj_basis=Decimal("7093.928514"),
        shares=Decimal("204"),
    )
    assert state.adj_btc == Decimal("0.17821032")


def test_month_proceeds():
    mp = MonthProceeds(
        btc_sold_per_share=Decimal("0.00000018"),
        proceeds_per_share_usd=Decimal("0.01070327"),
    )
    assert mp.btc_sold_per_share == Decimal("0.00000018")
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_models.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [x] **Step 3: Implement models**

`fbtc_taxgrinder/models.py`:
```python
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class LotEvent:
    type: str  # "sell"
    date: date
    shares: Decimal
    price_per_share: Decimal
    proceeds: Decimal
    disposition_id: str


@dataclass
class Lot:
    id: str
    purchase_date: date
    original_shares: Decimal
    price_per_share: Decimal
    total_cost: Decimal
    btc_per_share_on_purchase: Decimal
    source_file: str
    events: list[LotEvent] = field(default_factory=list)

    def shares_at_date(self, d: date) -> Decimal:
        """Return share count at a given date (sells reduce on their date)."""
        shares = self.original_shares
        for event in self.events:
            if event.type == "sell" and event.date <= d:
                shares -= event.shares
        return shares


@dataclass
class LotState:
    adj_btc: Decimal
    adj_basis: Decimal
    shares: Decimal


@dataclass
class MonthProceeds:
    btc_sold_per_share: Decimal
    proceeds_per_share_usd: Decimal


@dataclass
class YearProceeds:
    daily: dict[date, Decimal]  # date -> btc_per_share
    monthly: dict[date, MonthProceeds]  # month_end_date -> MonthProceeds
    source: str


@dataclass
class MonthResult:
    month: int
    days_held: Decimal
    days_in_month: Decimal
    shares: Decimal
    total_btc_sold: Decimal
    cost_basis_of_sold: Decimal
    total_expense: Decimal
    gain_loss: Decimal
    adj_btc: Decimal
    adj_basis: Decimal


@dataclass
class Disposition:
    lot_id: str
    disposition_id: str
    date_sold: date
    shares_sold: Decimal
    proceeds: Decimal
    disposed_btc: Decimal
    disposed_basis: Decimal
    gain_loss: Decimal


@dataclass
class YearResult:
    year: int
    lot_results: dict[str, list[MonthResult]]  # lot_id -> monthly results
    dispositions: list[Disposition]
    end_states: dict[str, LotState]  # lot_id -> year-end state
    total_investment_expense: Decimal
    total_reportable_gain: Decimal
    total_cost_basis_of_expense: Decimal
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_models.py -v`
Expected: All PASS

- [x] **Step 5: Check coverage**

Run: `pytest tests/test_models.py --cov=fbtc_taxgrinder.models --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage. If any uncovered lines, add tests before committing.

- [x] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/models.py tests/test_models.py
git commit -m "feat: add data models for lots, proceeds, results, and state"
```

---

## Task 3: JSON Data Access Layer ✅

> **Deviations:** Replaced hand-written per-type serializers with a generic `db/codec.py` using `dataclasses.asdict()` + `get_type_hints()` reconstruction. All db modules are thin file I/O wrappers. Added `tests/test_codec.py` for pure serialization tests. DB tests use mocks instead of filesystem per project convention.

**Files:**
- Create: `fbtc_taxgrinder/db/lots.py`
- Create: `fbtc_taxgrinder/db/proceeds.py`
- Create: `fbtc_taxgrinder/db/results.py`
- Create: `fbtc_taxgrinder/db/state.py`
- Create: `tests/conftest.py`
- Create: `tests/test_db.py`

- [x] **Step 1: Write failing tests for db layer**

`tests/conftest.py`:
```python
import pytest
from pathlib import Path


@pytest.fixture
def data_dir(tmp_path):
    """Create a temporary data directory with subdirs."""
    (tmp_path / "proceeds").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path
```

`tests/test_db.py`:
```python
from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import (
    Lot, LotEvent, LotState, MonthResult, Disposition,
    YearResult, MonthProceeds, YearProceeds,
)
from fbtc_taxgrinder.db import lots, proceeds, results, state


def test_lots_roundtrip(data_dir):
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell",
                date=date(2025, 12, 23),
                shares=Decimal("14"),
                price_per_share=Decimal("76.2201"),
                proceeds=Decimal("1067.08"),
                disposition_id="lot-1-sell-1",
            ),
        ],
    )
    lots.save(data_dir, [lot])
    loaded = lots.load(data_dir)
    assert len(loaded) == 1
    assert loaded[0].id == "lot-1"
    assert loaded[0].original_shares == Decimal("204")
    assert loaded[0].btc_per_share_on_purchase == Decimal("0.00087448")
    assert len(loaded[0].events) == 1
    assert loaded[0].events[0].shares == Decimal("14")


def test_lots_load_empty(data_dir):
    loaded = lots.load(data_dir)
    assert loaded == []


def test_proceeds_roundtrip(data_dir):
    yp = YearProceeds(
        daily={date(2024, 1, 11): Decimal("0.00087448")},
        monthly={
            date(2024, 8, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        },
        source="test.pdf",
    )
    proceeds.save(data_dir, 2024, yp)
    loaded = proceeds.load(data_dir, 2024)
    assert loaded is not None
    assert loaded.daily[date(2024, 1, 11)] == Decimal("0.00087448")
    assert loaded.monthly[date(2024, 8, 31)].btc_sold_per_share == Decimal("0.00000018")


def test_proceeds_load_missing(data_dir):
    loaded = proceeds.load(data_dir, 2024)
    assert loaded is None


def test_state_roundtrip(data_dir):
    states = {
        "lot-1": LotState(
            adj_btc=Decimal("0.17821032"),
            adj_basis=Decimal("7093.928514"),
            shares=Decimal("204"),
        ),
    }
    state.save(data_dir, 2024, states)
    loaded = state.load(data_dir, 2024)
    assert loaded is not None
    assert loaded["lot-1"].adj_btc == Decimal("0.17821032")


def test_state_load_missing(data_dir):
    loaded = state.load(data_dir, 2024)
    assert loaded is None


def test_results_roundtrip(data_dir):
    yr = YearResult(
        year=2024,
        lot_results={
            "lot-1": [
                MonthResult(
                    month=8, days_held=Decimal("31"), days_in_month=Decimal("31"),
                    shares=Decimal("204"), total_btc_sold=Decimal("0.00003672"),
                    cost_basis_of_sold=Decimal("1.461695179"),
                    total_expense=Decimal("2.18346708"),
                    gain_loss=Decimal("0.7217719012"),
                    adj_btc=Decimal("0.17835720"),
                    adj_basis=Decimal("7099.778305"),
                ),
            ],
        },
        dispositions=[],
        end_states={},
        total_investment_expense=Decimal("2.18346708"),
        total_reportable_gain=Decimal("0.7217719012"),
        total_cost_basis_of_expense=Decimal("1.461695179"),
    )
    results.save(data_dir, yr)
    loaded = results.load(data_dir, 2024)
    assert loaded is not None
    assert loaded.year == 2024
    assert len(loaded.lot_results["lot-1"]) == 1
    assert loaded.lot_results["lot-1"][0].adj_btc == Decimal("0.17835720")
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_db.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [x] **Step 3: Implement db/lots.py**

```python
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
```

- [x] **Step 4: Implement db/proceeds.py**

```python
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
```

- [x] **Step 5: Implement db/state.py**

```python
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
```

- [x] **Step 6: Implement db/results.py**

```python
from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from fbtc_taxgrinder.models import Disposition, LotState, MonthResult, YearResult


def save(data_dir: Path, yr: YearResult) -> None:
    path = data_dir / "results" / f"{yr.year}.json"
    data = {
        "year": yr.year,
        "end_states": {
            lot_id: {
                "adj_btc": str(s.adj_btc),
                "adj_basis": str(s.adj_basis),
                "shares": str(s.shares),
            }
            for lot_id, s in yr.end_states.items()
        },
        "lot_results": {
            lot_id: [
                {
                    "month": mr.month,
                    "days_held": str(mr.days_held),
                    "days_in_month": str(mr.days_in_month),
                    "shares": str(mr.shares),
                    "total_btc_sold": str(mr.total_btc_sold),
                    "cost_basis_of_sold": str(mr.cost_basis_of_sold),
                    "total_expense": str(mr.total_expense),
                    "gain_loss": str(mr.gain_loss),
                    "adj_btc": str(mr.adj_btc),
                    "adj_basis": str(mr.adj_basis),
                }
                for mr in results
            ]
            for lot_id, results in yr.lot_results.items()
        },
        "dispositions": [
            {
                "lot_id": d.lot_id,
                "disposition_id": d.disposition_id,
                "date_sold": d.date_sold.isoformat(),
                "shares_sold": str(d.shares_sold),
                "proceeds": str(d.proceeds),
                "disposed_btc": str(d.disposed_btc),
                "disposed_basis": str(d.disposed_basis),
                "gain_loss": str(d.gain_loss),
            }
            for d in yr.dispositions
        ],
        "total_investment_expense": str(yr.total_investment_expense),
        "total_reportable_gain": str(yr.total_reportable_gain),
        "total_cost_basis_of_expense": str(yr.total_cost_basis_of_expense),
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load(data_dir: Path, year: int) -> YearResult | None:
    path = data_dir / "results" / f"{year}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    lot_results = {
        lot_id: [
            MonthResult(
                month=mr["month"],
                days_held=Decimal(mr["days_held"]),
                days_in_month=Decimal(mr["days_in_month"]),
                shares=Decimal(mr["shares"]),
                total_btc_sold=Decimal(mr["total_btc_sold"]),
                cost_basis_of_sold=Decimal(mr["cost_basis_of_sold"]),
                total_expense=Decimal(mr["total_expense"]),
                gain_loss=Decimal(mr["gain_loss"]),
                adj_btc=Decimal(mr["adj_btc"]),
                adj_basis=Decimal(mr["adj_basis"]),
            )
            for mr in results
        ]
        for lot_id, results in data["lot_results"].items()
    }
    dispositions = [
        Disposition(
            lot_id=d["lot_id"],
            disposition_id=d["disposition_id"],
            date_sold=date.fromisoformat(d["date_sold"]),
            shares_sold=Decimal(d["shares_sold"]),
            proceeds=Decimal(d["proceeds"]),
            disposed_btc=Decimal(d["disposed_btc"]),
            disposed_basis=Decimal(d["disposed_basis"]),
            gain_loss=Decimal(d["gain_loss"]),
        )
        for d in data["dispositions"]
    ]
    end_states = {
        lot_id: LotState(
            adj_btc=Decimal(v["adj_btc"]),
            adj_basis=Decimal(v["adj_basis"]),
            shares=Decimal(v["shares"]),
        )
        for lot_id, v in data.get("end_states", {}).items()
    }
    return YearResult(
        year=data["year"],
        lot_results=lot_results,
        dispositions=dispositions,
        end_states=end_states,
        total_investment_expense=Decimal(data["total_investment_expense"]),
        total_reportable_gain=Decimal(data["total_reportable_gain"]),
        total_cost_basis_of_expense=Decimal(data["total_cost_basis_of_expense"]),
    )
```

- [x] **Step 7: Run tests to verify they pass**

Run: `pytest tests/test_db.py -v`
Expected: All PASS

- [x] **Step 8: Check coverage**

Run: `pytest tests/test_db.py --cov=fbtc_taxgrinder.db --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage on all db modules. Add tests for any uncovered branches.

- [x] **Step 9: Commit**

```bash
git add fbtc_taxgrinder/db/ tests/conftest.py tests/test_db.py
git commit -m "feat: add JSON data access layer for lots, proceeds, results, state"
```

---

## Task 4: Core Engine — Single Period Computation ✅

The foundational computation: Steps 1-6 for a single period (a contiguous span of days within a month). Everything else builds on this.

**Files:**
- Create: `fbtc_taxgrinder/engine/compute.py`
- Create: `tests/test_compute.py`

- [x] **Step 1: Write failing test for compute_period**

`tests/test_compute.py`:
```python
from decimal import Decimal
from fbtc_taxgrinder.engine.compute import compute_period


def test_compute_period_full_month():
    """Lot-1, August 2024: 204 shares, full month (31 days), first expense month."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("204"),
        adj_btc=Decimal("0.17839392"),       # 0.00087448 * 204
        adj_basis=Decimal("7101.24"),
        original_total_cost=Decimal("7101.24"),
        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    # Step 2: btc_sold_per_share = (31/31) * 0.00000018 = 0.00000018
    #         total_btc_sold = 0.00000018 * 204 = 0.00003672
    assert result.total_btc_sold == Decimal("0.00000018") * Decimal("204")
    # Step 4: total_expense = 0.01070327 * 204 = 2.18346708
    assert result.total_expense == Decimal("0.01070327") * Decimal("204")
    # Step 6: adj_btc = 0.17839392 - 0.00003672
    assert result.adj_btc == Decimal("0.17839392") - Decimal("0.00003672")


def test_compute_period_zero_expense():
    """Month with no BTC sold (Jan-Jul 2024)."""
    result = compute_period(
        days_held=Decimal("31"),
        days_in_month=Decimal("31"),
        shares=Decimal("204"),
        adj_btc=Decimal("0.17839392"),
        adj_basis=Decimal("7101.24"),
        original_total_cost=Decimal("7101.24"),
        monthly_btc_sold_per_share=Decimal("0"),
        monthly_proceeds_per_share_usd=Decimal("0"),
    )
    assert result.total_btc_sold == Decimal("0")
    assert result.total_expense == Decimal("0")
    assert result.gain_loss == Decimal("0")
    assert result.adj_btc == Decimal("0.17839392")
    assert result.adj_basis == Decimal("7101.24")


def test_compute_period_prorated():
    """Lot purchased Aug 19, first month Aug: days_held = 12 out of 31."""
    result = compute_period(
        days_held=Decimal("12"),
        days_in_month=Decimal("31"),
        shares=Decimal("1"),
        adj_btc=Decimal("0.00087437"),
        adj_basis=Decimal("51.3995"),
        original_total_cost=Decimal("51.3995"),
        monthly_btc_sold_per_share=Decimal("0.00000018"),
        monthly_proceeds_per_share_usd=Decimal("0.01070327"),
    )
    # btc_sold = (12/31) * 0.00000018 * 1
    expected_btc_sold = Decimal("12") / Decimal("31") * Decimal("0.00000018")
    assert result.total_btc_sold == expected_btc_sold
    # expense = (12/31) * 0.01070327 * 1
    expected_expense = Decimal("12") / Decimal("31") * Decimal("0.01070327")
    assert result.total_expense == expected_expense
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_compute.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [x] **Step 3: Implement compute_period**

`fbtc_taxgrinder/engine/compute.py`:
```python
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PeriodResult:
    total_btc_sold: Decimal
    cost_basis_of_sold: Decimal
    total_expense: Decimal
    gain_loss: Decimal
    adj_btc: Decimal
    adj_basis: Decimal


def compute_period(
    *,
    days_held: Decimal,
    days_in_month: Decimal,
    shares: Decimal,
    adj_btc: Decimal,
    adj_basis: Decimal,
    original_total_cost: Decimal,
    monthly_btc_sold_per_share: Decimal,
    monthly_proceeds_per_share_usd: Decimal,
) -> PeriodResult:
    """Run Steps 1-6 for a single contiguous period within a month."""
    if days_held == 0 or shares == 0:
        return PeriodResult(
            total_btc_sold=Decimal("0"),
            cost_basis_of_sold=Decimal("0"),
            total_expense=Decimal("0"),
            gain_loss=Decimal("0"),
            adj_btc=adj_btc,
            adj_basis=adj_basis,
        )

    proration = days_held / days_in_month

    # Step 2
    total_btc_sold = Decimal("0")
    cost_basis_of_sold = Decimal("0")
    if monthly_btc_sold_per_share != 0:
        btc_sold_per_share = proration * monthly_btc_sold_per_share
        total_btc_sold = btc_sold_per_share * shares
        # Step 3
        cost_basis_of_sold = (total_btc_sold / adj_btc) * original_total_cost

    # Step 4
    expense_per_share = proration * monthly_proceeds_per_share_usd
    total_expense = expense_per_share * shares

    # Step 5
    gain_loss = total_expense - cost_basis_of_sold

    # Step 6
    new_adj_btc = adj_btc - total_btc_sold
    new_adj_basis = adj_basis - cost_basis_of_sold

    return PeriodResult(
        total_btc_sold=total_btc_sold,
        cost_basis_of_sold=cost_basis_of_sold,
        total_expense=total_expense,
        gain_loss=gain_loss,
        adj_btc=new_adj_btc,
        adj_basis=new_adj_basis,
    )
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_compute.py -v`
Expected: All PASS

- [x] **Step 5: Check coverage**

Run: `pytest tests/test_compute.py --cov=fbtc_taxgrinder.engine.compute --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage. Add tests for uncovered branches.

- [x] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/engine/compute.py tests/test_compute.py
git commit -m "feat: implement compute_period — Steps 1-6 for a single period"
```

---

## Task 5: Engine — Monthly Computation With Sell Events ✅

> **Deviations:** Fixed Step 3 bug from plan: `compute_period` now uses `adj_basis` instead of `original_total_cost` for cost basis calculation, matching the WHFIT spec requirement that btc/basis pairs stay matched. Removed `original_total_cost` parameter. Added extensive edge case tests (sell on day 1, sell on last day, sell in purchase month, same-day sells, proportional disposition verification, full liquidation zeroes state, state chaining across months).

Build on `compute_period` to handle a full month for a lot, including mid-month sells (3-phase split).

**Files:**
- Modify: `fbtc_taxgrinder/engine/compute.py`
- Create: `tests/test_sells.py`
- Create: `tests/test_proration.py`

- [x] **Step 1: Write failing tests for compute_lot_month**

`tests/test_proration.py`:
```python
from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import Lot, MonthProceeds
from fbtc_taxgrinder.engine.compute import compute_lot_month, LotMonthInput


def test_first_month_proration():
    """Lot purchased Aug 19: days_held in Aug = 31 - 19 = 12."""
    result = compute_lot_month(LotMonthInput(
        lot=Lot(
            id="lot-10", purchase_date=date(2024, 8, 19),
            original_shares=Decimal("1"), price_per_share=Decimal("51.3995"),
            total_cost=Decimal("51.3995"),
            btc_per_share_on_purchase=Decimal("0.00087437"),
            source_file="test.csv", events=[],
        ),
        year=2024, month=8,
        adj_btc=Decimal("0.00087437"),
        adj_basis=Decimal("51.3995"),
        shares=Decimal("1"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01070327"),
        ),
    ))
    assert result.month_result.days_held == Decimal("12")
    assert result.month_result.days_in_month == Decimal("31")


def test_full_month_after_purchase():
    """Lot purchased Aug 19: September is a full month (30 days)."""
    result = compute_lot_month(LotMonthInput(
        lot=Lot(
            id="lot-10", purchase_date=date(2024, 8, 19),
            original_shares=Decimal("1"), price_per_share=Decimal("51.3995"),
            total_cost=Decimal("51.3995"),
            btc_per_share_on_purchase=Decimal("0.00087437"),
            source_file="test.csv", events=[],
        ),
        year=2024, month=9,
        adj_btc=Decimal("0.00087430"),
        adj_basis=Decimal("51.39"),
        shares=Decimal("1"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01124247"),
        ),
    ))
    assert result.month_result.days_held == Decimal("30")


def test_lot_not_yet_active():
    """Lot purchased Sep 9: should skip August entirely."""
    result = compute_lot_month(LotMonthInput(
        lot=Lot(
            id="lot-12", purchase_date=date(2024, 9, 9),
            original_shares=Decimal("126"), price_per_share=Decimal("49.50"),
            total_cost=Decimal("6237.00"),
            btc_per_share_on_purchase=Decimal("0.00087425"),
            source_file="test.csv", events=[],
        ),
        year=2024, month=8,
        adj_btc=Decimal("0.11015550"),
        adj_basis=Decimal("6237.00"),
        shares=Decimal("126"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01070327"),
        ),
    ))
    assert result is None  # Not active this month


def test_purchased_first_of_month():
    """Lot purchased Oct 1: days_held = 31 - 1 = 30 (purchase day not counted)."""
    result = compute_lot_month(LotMonthInput(
        lot=Lot(
            id="lot-x", purchase_date=date(2024, 10, 1),
            original_shares=Decimal("10"), price_per_share=Decimal("50.00"),
            total_cost=Decimal("500.00"),
            btc_per_share_on_purchase=Decimal("0.00087401"),
            source_file="test.csv", events=[],
        ),
        year=2024, month=10,
        adj_btc=Decimal("0.0087401"),
        adj_basis=Decimal("500.00"),
        shares=Decimal("10"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01236501"),
        ),
    ))
    assert result is not None
    assert result.month_result.days_held == Decimal("30")
    assert result.month_result.days_in_month == Decimal("31")


def test_february_leap_year():
    """Lot active in Feb 2024 (leap year): days_in_month = 29."""
    result = compute_lot_month(LotMonthInput(
        lot=Lot(
            id="lot-x", purchase_date=date(2024, 1, 15),
            original_shares=Decimal("10"), price_per_share=Decimal("50.00"),
            total_cost=Decimal("500.00"),
            btc_per_share_on_purchase=Decimal("0.00087448"),
            source_file="test.csv", events=[],
        ),
        year=2024, month=2,
        adj_btc=Decimal("0.0087448"),
        adj_basis=Decimal("500.00"),
        shares=Decimal("10"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0"),
            proceeds_per_share_usd=Decimal("0"),
        ),
    ))
    assert result is not None
    assert result.month_result.days_in_month == Decimal("29")
    assert result.month_result.days_held == Decimal("29")  # Full month (purchased prior month)


def test_purchased_last_day_of_month():
    """Lot purchased Aug 31: days_held = 31-31 = 0, skip to September."""
    result = compute_lot_month(LotMonthInput(
        lot=Lot(
            id="lot-x", purchase_date=date(2024, 8, 31),
            original_shares=Decimal("10"), price_per_share=Decimal("50.00"),
            total_cost=Decimal("500.00"),
            btc_per_share_on_purchase=Decimal("0.00087430"),
            source_file="test.csv", events=[],
        ),
        year=2024, month=8,
        adj_btc=Decimal("0.0087430"),
        adj_basis=Decimal("500.00"),
        shares=Decimal("10"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01070327"),
        ),
    ))
    assert result is None  # days_held = 0, not active
```

`tests/test_sells.py`:
```python
from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import Lot, LotEvent, MonthProceeds
from fbtc_taxgrinder.engine.compute import compute_lot_month, LotMonthInput


def test_sell_mid_month():
    """Sell 14 of 204 shares on Dec 23. Month split into 3 phases."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell", date=date(2025, 12, 23),
                shares=Decimal("14"), price_per_share=Decimal("76.2201"),
                proceeds=Decimal("1067.08"), disposition_id="lot-1-sell-1",
            ),
        ],
    )
    result = compute_lot_month(LotMonthInput(
        lot=lot, year=2025, month=12,
        adj_btc=Decimal("0.17800000"),
        adj_basis=Decimal("7080.00"),
        shares=Decimal("204"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01581176"),
        ),
    ))
    assert result is not None
    # Should have one disposition
    assert len(result.dispositions) == 1
    d = result.dispositions[0]
    assert d.shares_sold == Decimal("14")
    assert d.lot_id == "lot-1"
    # Post-sell shares should be 190
    assert result.new_state.shares == Decimal("190")


def test_sell_full_liquidation():
    """Sell all shares — Phase 3 skipped."""
    lot = Lot(
        id="lot-x", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("10"), price_per_share=Decimal("50.00"),
        total_cost=Decimal("500.00"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell", date=date(2024, 10, 15),
                shares=Decimal("10"), price_per_share=Decimal("60.00"),
                proceeds=Decimal("600.00"), disposition_id="lot-x-sell-1",
            ),
        ],
    )
    result = compute_lot_month(LotMonthInput(
        lot=lot, year=2024, month=10,
        adj_btc=Decimal("0.00874000"),
        adj_basis=Decimal("499.50"),
        shares=Decimal("10"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01236501"),
        ),
    ))
    assert result is not None
    assert len(result.dispositions) == 1
    assert result.new_state.shares == Decimal("0")


def test_two_sells_same_month():
    """Two sells in the same month: expense -> dispose -> expense -> dispose -> expense."""
    lot = Lot(
        id="lot-x", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("100"), price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell", date=date(2025, 3, 10),
                shares=Decimal("20"), price_per_share=Decimal("60.00"),
                proceeds=Decimal("1200.00"), disposition_id="lot-x-sell-1",
            ),
            LotEvent(
                type="sell", date=date(2025, 3, 20),
                shares=Decimal("30"), price_per_share=Decimal("65.00"),
                proceeds=Decimal("1950.00"), disposition_id="lot-x-sell-2",
            ),
        ],
    )
    result = compute_lot_month(LotMonthInput(
        lot=lot, year=2025, month=3,
        adj_btc=Decimal("0.08700000"),
        adj_basis=Decimal("4950.00"),
        shares=Decimal("100"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01509769"),
        ),
    ))
    assert result is not None
    assert len(result.dispositions) == 2
    assert result.dispositions[0].shares_sold == Decimal("20")
    assert result.dispositions[1].shares_sold == Decimal("30")
    assert result.new_state.shares == Decimal("50")


def test_no_sell_event_normal_month():
    """Normal month with no sell — no dispositions."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv", events=[],
    )
    result = compute_lot_month(LotMonthInput(
        lot=lot, year=2024, month=8,
        adj_btc=Decimal("0.17839392"),
        adj_basis=Decimal("7101.24"),
        shares=Decimal("204"),
        month_proceeds=MonthProceeds(
            btc_sold_per_share=Decimal("0.00000018"),
            proceeds_per_share_usd=Decimal("0.01070327"),
        ),
    ))
    assert result is not None
    assert len(result.dispositions) == 0
```

- [x] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_proration.py tests/test_sells.py -v`
Expected: FAIL — `ImportError` for `compute_lot_month`

- [x] **Step 3: Implement compute_lot_month**

Add to `fbtc_taxgrinder/engine/compute.py`:

```python
import calendar
from datetime import date

from fbtc_taxgrinder.models import (
    Lot, LotState, MonthProceeds, MonthResult, Disposition,
)


@dataclass
class LotMonthInput:
    lot: Lot
    year: int
    month: int
    adj_btc: Decimal
    adj_basis: Decimal
    shares: Decimal
    month_proceeds: MonthProceeds


@dataclass
class LotMonthOutput:
    month_result: MonthResult
    dispositions: list[Disposition]
    new_state: LotState


def _month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def _month_start(year: int, month: int) -> date:
    return date(year, month, 1)


def compute_lot_month(inp: LotMonthInput) -> LotMonthOutput | None:
    """Compute one month for one lot, handling mid-month sells."""
    month_end = _month_end(inp.year, inp.month)
    month_start_date = _month_start(inp.year, inp.month)
    days_in_month = Decimal(str(calendar.monthrange(inp.year, inp.month)[1]))

    # Check if lot is active this month
    if inp.lot.purchase_date > month_end:
        return None

    # Determine base days_held for the full month
    if inp.lot.purchase_date >= month_start_date:
        # First month: prorate from purchase date
        full_days_held = Decimal(str((month_end - inp.lot.purchase_date).days))
        if full_days_held == 0:
            return None  # Purchased on last day, starts next month
        period_start = inp.lot.purchase_date
    else:
        full_days_held = days_in_month
        period_start = month_start_date

    # Find sell events in this month for this lot
    sell_events = [
        e for e in inp.lot.events
        if e.type == "sell"
        and e.date.year == inp.year
        and e.date.month == inp.month
    ]
    sell_events.sort(key=lambda e: e.date)

    adj_btc = inp.adj_btc
    adj_basis = inp.adj_basis
    shares = inp.shares
    total_btc_sold = Decimal("0")
    total_cost_basis = Decimal("0")
    total_expense = Decimal("0")
    total_gain_loss = Decimal("0")
    dispositions: list[Disposition] = []

    if not sell_events:
        # Simple case: no sells, run full period
        pr = compute_period(
            days_held=full_days_held,
            days_in_month=days_in_month,
            shares=shares,
            adj_btc=adj_btc,
            adj_basis=adj_basis,
            original_total_cost=inp.lot.total_cost,
            monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
            monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
        )
        return LotMonthOutput(
            month_result=MonthResult(
                month=inp.month,
                days_held=full_days_held,
                days_in_month=days_in_month,
                shares=shares,
                total_btc_sold=pr.total_btc_sold,
                cost_basis_of_sold=pr.cost_basis_of_sold,
                total_expense=pr.total_expense,
                gain_loss=pr.gain_loss,
                adj_btc=pr.adj_btc,
                adj_basis=pr.adj_basis,
            ),
            dispositions=[],
            new_state=LotState(adj_btc=pr.adj_btc, adj_basis=pr.adj_basis, shares=shares),
        )

    # Complex case: sells split the month into phases
    current_start = period_start

    for event in sell_events:
        # Phase 1: Pre-sell expense computation
        pre_days = Decimal(str((event.date - current_start).days))
        if pre_days > 0:
            pr = compute_period(
                days_held=pre_days,
                days_in_month=days_in_month,
                shares=shares,
                adj_btc=adj_btc,
                adj_basis=adj_basis,
                original_total_cost=inp.lot.total_cost,
                monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
                monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
            )
            total_btc_sold += pr.total_btc_sold
            total_cost_basis += pr.cost_basis_of_sold
            total_expense += pr.total_expense
            total_gain_loss += pr.gain_loss
            adj_btc = pr.adj_btc
            adj_basis = pr.adj_basis

        # Phase 2: Disposition
        disposed_btc = adj_btc * (event.shares / shares)
        disposed_basis = adj_basis * (event.shares / shares)
        disposition_gain_loss = event.proceeds - disposed_basis

        dispositions.append(Disposition(
            lot_id=inp.lot.id,
            disposition_id=event.disposition_id,
            date_sold=event.date,
            shares_sold=event.shares,
            proceeds=event.proceeds,
            disposed_btc=disposed_btc,
            disposed_basis=disposed_basis,
            gain_loss=disposition_gain_loss,
        ))

        adj_btc -= disposed_btc
        adj_basis -= disposed_basis
        shares -= event.shares
        current_start = event.date

    # Phase 3: Post-sell expense computation (if shares remain)
    if shares > 0:
        post_days = Decimal(str((month_end - current_start).days))
        if post_days > 0:
            pr = compute_period(
                days_held=post_days,
                days_in_month=days_in_month,
                shares=shares,
                adj_btc=adj_btc,
                adj_basis=adj_basis,
                original_total_cost=inp.lot.total_cost,
                monthly_btc_sold_per_share=inp.month_proceeds.btc_sold_per_share,
                monthly_proceeds_per_share_usd=inp.month_proceeds.proceeds_per_share_usd,
            )
            total_btc_sold += pr.total_btc_sold
            total_cost_basis += pr.cost_basis_of_sold
            total_expense += pr.total_expense
            total_gain_loss += pr.gain_loss
            adj_btc = pr.adj_btc
            adj_basis = pr.adj_basis

    return LotMonthOutput(
        month_result=MonthResult(
            month=inp.month,
            days_held=full_days_held,  # Total days lot was active in month
            days_in_month=days_in_month,
            shares=inp.shares,  # Starting shares for the month
            total_btc_sold=total_btc_sold,
            cost_basis_of_sold=total_cost_basis,
            total_expense=total_expense,
            gain_loss=total_gain_loss,
            adj_btc=adj_btc,
            adj_basis=adj_basis,
        ),
        dispositions=dispositions,
        new_state=LotState(adj_btc=adj_btc, adj_basis=adj_basis, shares=shares),
    )
```

- [x] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_proration.py tests/test_sells.py tests/test_compute.py -v`
Expected: All PASS

- [x] **Step 5: Check coverage**

Run: `pytest tests/test_proration.py tests/test_sells.py tests/test_compute.py --cov=fbtc_taxgrinder.engine.compute --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage on compute module including sell paths. Add tests for uncovered branches.

- [x] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/engine/compute.py tests/test_proration.py tests/test_sells.py
git commit -m "feat: implement compute_lot_month with sell event 3-phase split"
```

---

## Task 6: Engine — Full Year Computation

Wire `compute_lot_month` into `compute_year` which processes all lots across all months with state chaining.

**Files:**
- Modify: `fbtc_taxgrinder/engine/compute.py`
- Modify: `tests/test_compute.py`

- [ ] **Step 1: Write failing test for compute_year**

Add to `tests/test_compute.py`:
```python
from datetime import date
from fbtc_taxgrinder.models import (
    Lot, LotState, MonthProceeds, YearProceeds,
)
from fbtc_taxgrinder.engine.compute import compute_year


def test_compute_year_single_lot_single_month():
    """Simplest case: one lot, one active month (Aug 2024), full month."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv", events=[],
    )
    proceeds = YearProceeds(
        daily={date(2024, 1, 25): Decimal("0.00087448")},
        monthly={
            date(2024, 8, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        },
        source="test",
    )
    result = compute_year(
        lots=[lot],
        proceeds=proceeds,
        prior_state=None,
        year=2024,
    )
    assert "lot-1" in result.lot_results
    # Aug is month 8, should be the only result
    aug = [r for r in result.lot_results["lot-1"] if r.month == 8]
    assert len(aug) == 1
    assert aug[0].shares == Decimal("204")


def test_compute_year_chain_validation_error():
    """Lot from 2024 computing 2026 without 2025 state should error."""
    lot = Lot(
        id="lot-1", purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"), price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv", events=[],
    )
    proceeds = YearProceeds(
        daily={}, monthly={}, source="test",
    )
    import pytest
    with pytest.raises(ValueError, match="requires 2025 results"):
        compute_year(
            lots=[lot],
            proceeds=proceeds,
            prior_state={"lot-1": LotState(
                adj_btc=Decimal("0.17821032"),
                adj_basis=Decimal("7093.928514"),
                shares=Decimal("204"),
            )},
            year=2026,
        )
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_compute.py::test_compute_year_single_lot_single_month tests/test_compute.py::test_compute_year_chain_validation_error -v`
Expected: FAIL — `ImportError` for `compute_year`

- [ ] **Step 3: Implement compute_year**

Add to `fbtc_taxgrinder/engine/compute.py`:
```python
def compute_year(
    *,
    lots: list[Lot],
    proceeds: YearProceeds,
    prior_state: dict[str, LotState] | None,
    year: int,
) -> YearResult:
    """Compute all lots for a full year, chaining monthly state."""
    all_lot_results: dict[str, list[MonthResult]] = {}
    all_dispositions: list[Disposition] = []
    end_states: dict[str, LotState] = {}

    for lot in lots:
        # Determine initial state for this lot
        if lot.purchase_date.year == year:
            # New lot this year
            initial_btc = lot.btc_per_share_on_purchase * lot.original_shares
            state = LotState(
                adj_btc=initial_btc,
                adj_basis=lot.total_cost,
                shares=lot.original_shares,
            )
        elif prior_state and lot.id in prior_state:
            state = prior_state[lot.id]
        else:
            # Check if lot needs prior year state
            if lot.purchase_date.year < year:
                raise ValueError(
                    f"Lot {lot.id} (purchased {lot.purchase_date.isoformat()}) "
                    f"requires {year - 1} results before computing {year}"
                )
            continue  # Future lot, skip

        # Skip fully liquidated lots
        if state.shares == 0:
            end_states[lot.id] = state
            continue

        lot_results: list[MonthResult] = []

        for month in range(1, 13):
            month_end = _month_end(year, month)

            # Find month-end proceeds (may be absent = zero expense)
            mp = proceeds.monthly.get(month_end)
            if mp is None:
                mp = MonthProceeds(
                    btc_sold_per_share=Decimal("0"),
                    proceeds_per_share_usd=Decimal("0"),
                )

            output = compute_lot_month(LotMonthInput(
                lot=lot,
                year=year,
                month=month,
                adj_btc=state.adj_btc,
                adj_basis=state.adj_basis,
                shares=state.shares,
                month_proceeds=mp,
            ))

            if output is None:
                continue

            lot_results.append(output.month_result)
            all_dispositions.extend(output.dispositions)
            state = output.new_state

        all_lot_results[lot.id] = lot_results
        end_states[lot.id] = state

    # Compute annual summary
    total_expense = sum(
        (mr.total_expense for results in all_lot_results.values() for mr in results),
        Decimal("0"),
    )
    total_gain = sum(
        (mr.gain_loss for results in all_lot_results.values() for mr in results),
        Decimal("0"),
    )

    return YearResult(
        year=year,
        lot_results=all_lot_results,
        dispositions=all_dispositions,
        end_states=end_states,
        total_investment_expense=total_expense,
        total_reportable_gain=total_gain,
        total_cost_basis_of_expense=total_expense - total_gain,
    )
```

- [ ] **Step 4: Run all engine tests**

Run: `pytest tests/test_compute.py tests/test_proration.py tests/test_sells.py -v`
Expected: All PASS

- [ ] **Step 5: Check coverage**

Run: `pytest tests/test_compute.py tests/test_proration.py tests/test_sells.py --cov=fbtc_taxgrinder.engine.compute --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage. Add tests for uncovered branches.

- [ ] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/engine/compute.py tests/test_compute.py
git commit -m "feat: implement compute_year — full year lot computation with state chaining"
```

---

## Task 7: Sell Matching Logic

**Files:**
- Create: `fbtc_taxgrinder/engine/matching.py`
- Create: `tests/test_matching.py`

- [ ] **Step 1: Write failing tests**

`tests/test_matching.py`:
```python
import pytest
from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.models import Lot
from fbtc_taxgrinder.engine.matching import match_sell_to_lot


def _make_lot(id: str, shares: str, purchase_date: date = date(2024, 1, 25)) -> Lot:
    return Lot(
        id=id, purchase_date=purchase_date,
        original_shares=Decimal(shares), price_per_share=Decimal("50.00"),
        total_cost=Decimal(shares) * Decimal("50.00"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv", events=[],
    )


def test_unique_match():
    lots = [_make_lot("lot-1", "100"), _make_lot("lot-2", "50")]
    matched = match_sell_to_lot(lots, sell_shares=Decimal("80"), sell_date=date(2024, 12, 1))
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
    matched = match_sell_to_lot(lots, sell_shares=Decimal("50"), sell_date=date(2024, 12, 1))
    assert matched.id == "lot-2"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_matching.py -v`
Expected: FAIL

- [ ] **Step 3: Implement matching**

`fbtc_taxgrinder/engine/matching.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_matching.py -v`
Expected: All PASS

- [ ] **Step 5: Check coverage**

Run: `pytest tests/test_matching.py --cov=fbtc_taxgrinder.engine.matching --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage. Add tests for uncovered branches.

- [ ] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/engine/matching.py tests/test_matching.py
git commit -m "feat: implement sell-to-lot matching with ambiguity detection"
```

---

## Task 8: Fidelity PDF Parser

**Files:**
- Create: `fbtc_taxgrinder/parsers/fidelity_pdf.py`
- Create: `tests/test_fidelity_parser.py`

Note: The Fidelity PDF uses text layout, not HTML tables. `pdfplumber` extracts text lines like:
- Daily rows: `1/11/2024 0.00087448`
- Month-end rows: `8/31/2024 0.00087430 0.00000018 0 .01070327` (note the spurious space in `0 .01070327`)

- [ ] **Step 1: Write failing test for PDF text line parsing**

`tests/test_fidelity_parser.py`:
```python
from decimal import Decimal
from datetime import date
from fbtc_taxgrinder.parsers.fidelity_pdf import parse_proceeds_line


def test_parse_daily_line():
    result = parse_proceeds_line("1/11/2024 0.00087448")
    assert result is not None
    assert result["date"] == date(2024, 1, 11)
    assert result["btc_per_share"] == Decimal("0.00087448")
    assert result["btc_sold_per_share"] is None


def test_parse_month_end_line():
    result = parse_proceeds_line("8/31/2024 0.00087430 0.00000018 0 .01070327")
    assert result is not None
    assert result["date"] == date(2024, 8, 31)
    assert result["btc_per_share"] == Decimal("0.00087430")
    assert result["btc_sold_per_share"] == Decimal("0.00000018")
    assert result["proceeds_per_share_usd"] == Decimal("0.01070327")


def test_parse_month_end_line_no_space_in_decimal():
    """2025 PDF may not have the space issue."""
    result = parse_proceeds_line("1/31/2025 0.00087339 0.00000018 0.01806356")
    assert result is not None
    assert result["proceeds_per_share_usd"] == Decimal("0.01806356")


def test_parse_header_line():
    result = parse_proceeds_line("Bitcoin Per Per Share Bitcoin Sold To Proceeds Per Share (USD)")
    assert result is None


def test_parse_empty_line():
    result = parse_proceeds_line("")
    assert result is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_fidelity_parser.py -v`
Expected: FAIL

- [ ] **Step 3: Implement line parser**

`fbtc_taxgrinder/parsers/fidelity_pdf.py`:
```python
from __future__ import annotations

import re
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber
import requests

from fbtc_taxgrinder.models import MonthProceeds, YearProceeds


def parse_proceeds_line(line: str) -> dict | None:
    """Parse a single line from the Fidelity Gross Proceeds PDF text.

    Returns dict with date, btc_per_share, and optionally btc_sold_per_share
    and proceeds_per_share_usd. Returns None for non-data lines.
    """
    line = line.strip()
    if not line:
        return None

    # Fix spurious spaces in decimals: "0 .01070327" -> "0.01070327"
    line = re.sub(r"(\d)\s+\.", r"\1.", line)

    # Match: date btc_per_share [btc_sold proceeds]
    # Date format: M/D/YYYY
    match = re.match(
        r"^(\d{1,2}/\d{1,2}/\d{4})\s+"
        r"(\d+\.\d+)"
        r"(?:\s+(\d+\.\d+)\s+(\d+\.\d+))?$",
        line,
    )
    if not match:
        return None

    try:
        parts = match.group(1).split("/")
        d = date(int(parts[2]), int(parts[0]), int(parts[1]))
        btc_per_share = Decimal(match.group(2))
    except (ValueError, InvalidOperation):
        return None

    result: dict = {
        "date": d,
        "btc_per_share": btc_per_share,
        "btc_sold_per_share": None,
        "proceeds_per_share_usd": None,
    }

    if match.group(3) and match.group(4):
        result["btc_sold_per_share"] = Decimal(match.group(3))
        result["proceeds_per_share_usd"] = Decimal(match.group(4))

    return result


def parse_fidelity_pdf(source: str) -> YearProceeds:
    """Parse a Fidelity WHFIT PDF from URL or local file path.

    Args:
        source: URL (http/https) or local file path.

    Returns:
        YearProceeds with daily and monthly data.
    """
    if source.startswith("http://") or source.startswith("https://"):
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            resp = requests.get(source, timeout=30)
            resp.raise_for_status()
            tmp.write(resp.content)
            tmp.close()
            pdf_path = tmp.name
        except Exception:
            Path(tmp.name).unlink(missing_ok=True)
            raise
    else:
        pdf_path = source

    try:
        daily: dict[date, Decimal] = {}
        monthly: dict[date, MonthProceeds] = {}

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split("\n"):
                    parsed = parse_proceeds_line(line)
                    if parsed is None:
                        continue
                    daily[parsed["date"]] = parsed["btc_per_share"]
                    if parsed["btc_sold_per_share"] is not None:
                        monthly[parsed["date"]] = MonthProceeds(
                            btc_sold_per_share=parsed["btc_sold_per_share"],
                            proceeds_per_share_usd=parsed["proceeds_per_share_usd"],
                        )
    finally:
        if source.startswith("http"):
            Path(pdf_path).unlink(missing_ok=True)

    source_name = source.split("/")[-1] if "/" in source else source
    return YearProceeds(daily=daily, monthly=monthly, source=source_name)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_fidelity_parser.py -v`
Expected: All PASS

- [ ] **Step 5: Check coverage**

Run: `pytest tests/test_fidelity_parser.py --cov=fbtc_taxgrinder.parsers.fidelity_pdf --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage. The `parse_fidelity_pdf` function itself touches I/O (URL download, pdfplumber) which is harder to unit-test — but `parse_proceeds_line` should be fully covered. Add tests for edge cases in line parsing if needed.

- [ ] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/parsers/fidelity_pdf.py tests/test_fidelity_parser.py
git commit -m "feat: implement Fidelity PDF parser with text line extraction"
```

---

## Task 9: ETrade CSV Parser

**Files:**
- Create: `fbtc_taxgrinder/parsers/etrade.py`
- Create: `tests/test_etrade_parser.py`

- [ ] **Step 1: Write failing tests**

`tests/test_etrade_parser.py`:
```python
import csv
from decimal import Decimal
from datetime import date
from pathlib import Path
from fbtc_taxgrinder.parsers.etrade import parse_etrade_csv


def _write_csv(path: Path, rows: list[dict]):
    fieldnames = [
        "Trade Date", "Order Type", "Security", "Cusip",
        "Transaction Description", "Quantity", "Executed Price",
        "Commission", "Net Amount",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_parse_buys_only(tmp_path):
    csv_path = tmp_path / "trades.csv"
    _write_csv(csv_path, [
        {
            "Trade Date": "1/25/2024", "Order Type": "Buy", "Security": "FBTC",
            "Cusip": "315948109", "Transaction Description": "FIDELITY WISE ORIGIN BITCOIN",
            "Quantity": "204", "Executed Price": "34.81",
            "Commission": "0.0000", "Net Amount": "7101.24",
        },
        {
            "Trade Date": "1/25/2024", "Order Type": "Buy", "Security": "VOO",
            "Cusip": "922908363", "Transaction Description": "VANGUARD S&P 500 ETF",
            "Quantity": "10", "Executed Price": "400.00",
            "Commission": "0.00", "Net Amount": "4000.00",
        },
    ])
    result = parse_etrade_csv(str(csv_path))
    assert len(result["buys"]) == 1
    assert result["buys"][0]["date"] == date(2024, 1, 25)
    assert result["buys"][0]["shares"] == Decimal("204")
    assert result["buys"][0]["price_per_share"] == Decimal("34.81")
    assert result["buys"][0]["total_cost"] == Decimal("7101.24")
    assert len(result["sells"]) == 0


def test_parse_sells(tmp_path):
    csv_path = tmp_path / "trades.csv"
    _write_csv(csv_path, [
        {
            "Trade Date": "12/23/2025", "Order Type": "Sell", "Security": "FBTC",
            "Cusip": "315948109",
            "Transaction Description": "FIDELITY WISE ORIGIN BITCOIN UNSOLICITED TRADE",
            "Quantity": "14", "Executed Price": "76.2201",
            "Commission": "0.0000", "Net Amount": "1067.08",
        },
    ])
    result = parse_etrade_csv(str(csv_path))
    assert len(result["sells"]) == 1
    assert result["sells"][0]["date"] == date(2025, 12, 23)
    assert result["sells"][0]["shares"] == Decimal("14")
    assert result["sells"][0]["price_per_share"] == Decimal("76.2201")
    assert result["sells"][0]["proceeds"] == Decimal("1067.08")


def test_chronological_order(tmp_path):
    csv_path = tmp_path / "trades.csv"
    _write_csv(csv_path, [
        {
            "Trade Date": "12/23/2025", "Order Type": "Sell", "Security": "FBTC",
            "Cusip": "315948109", "Transaction Description": "FBTC",
            "Quantity": "14", "Executed Price": "76.00",
            "Commission": "0.00", "Net Amount": "1064.00",
        },
        {
            "Trade Date": "1/25/2024", "Order Type": "Buy", "Security": "FBTC",
            "Cusip": "315948109", "Transaction Description": "FBTC",
            "Quantity": "204", "Executed Price": "34.81",
            "Commission": "0.00", "Net Amount": "7101.24",
        },
    ])
    result = parse_etrade_csv(str(csv_path))
    # Buys and sells should each be sorted by date
    assert result["buys"][0]["date"] == date(2024, 1, 25)
    assert result["sells"][0]["date"] == date(2025, 12, 23)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_etrade_parser.py -v`
Expected: FAIL

- [ ] **Step 3: Implement ETrade parser**

`fbtc_taxgrinder/parsers/etrade.py`:
```python
from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path


def parse_etrade_csv(file_path: str) -> dict:
    """Parse an ETrade CSV/XLS file and extract FBTC transactions.

    Returns dict with 'buys' and 'sells' lists, each sorted by date.
    Each buy: {date, shares, price_per_share}
    Each sell: {date, shares, price_per_share, proceeds}
    """
    buys: list[dict] = []
    sells: list[dict] = []

    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Security"].strip() != "FBTC":
                continue

            parts = row["Trade Date"].strip().split("/")
            trade_date = date(int(parts[2]), int(parts[0]), int(parts[1]))
            shares = Decimal(row["Quantity"].strip())
            price = Decimal(row["Executed Price"].strip())
            order_type = row["Order Type"].strip()

            if order_type == "Buy":
                net_amount = Decimal(row["Net Amount"].strip())
                buys.append({
                    "date": trade_date,
                    "shares": shares,
                    "price_per_share": price,
                    "total_cost": net_amount,
                })
            elif order_type == "Sell":
                proceeds = Decimal(row["Net Amount"].strip())
                sells.append({
                    "date": trade_date,
                    "shares": shares,
                    "price_per_share": price,
                    "proceeds": proceeds,
                })

    buys.sort(key=lambda x: x["date"])
    sells.sort(key=lambda x: x["date"])

    return {"buys": buys, "sells": sells}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_etrade_parser.py -v`
Expected: All PASS

- [ ] **Step 5: Check coverage**

Run: `pytest tests/test_etrade_parser.py --cov=fbtc_taxgrinder.parsers.etrade --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage. Add tests for uncovered branches.

- [ ] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/parsers/etrade.py tests/test_etrade_parser.py
git commit -m "feat: implement ETrade CSV parser with FBTC filtering"
```

---

## Task 10: CSV Export

**Files:**
- Create: `fbtc_taxgrinder/export/csv_export.py`
- Create: `tests/test_csv_export.py`

- [ ] **Step 1: Write failing test**

`tests/test_csv_export.py`:
```python
import csv
from decimal import Decimal
from datetime import date
from pathlib import Path
from fbtc_taxgrinder.models import MonthResult, Disposition, YearResult
from fbtc_taxgrinder.export.csv_export import export_year_csv


def test_export_creates_three_files(tmp_path):
    yr = YearResult(
        year=2024,
        lot_results={
            "lot-1": [
                MonthResult(
                    month=8, days_held=Decimal("31"), days_in_month=Decimal("31"),
                    shares=Decimal("204"), total_btc_sold=Decimal("0.00003672"),
                    cost_basis_of_sold=Decimal("1.46"),
                    total_expense=Decimal("2.18"),
                    gain_loss=Decimal("0.72"),
                    adj_btc=Decimal("0.17835720"),
                    adj_basis=Decimal("7099.78"),
                ),
            ],
        },
        dispositions=[
            Disposition(
                lot_id="lot-1", disposition_id="lot-1-sell-1",
                date_sold=date(2024, 12, 23), shares_sold=Decimal("14"),
                proceeds=Decimal("1067.08"), disposed_btc=Decimal("0.012"),
                disposed_basis=Decimal("487.12"), gain_loss=Decimal("579.96"),
            ),
        ],
        end_states={},
        total_investment_expense=Decimal("2.18"),
        total_reportable_gain=Decimal("0.72"),
        total_cost_basis_of_expense=Decimal("1.46"),
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    export_year_csv(yr, output_dir)

    monthly_path = output_dir / "2024_monthly.csv"
    dispositions_path = output_dir / "2024_dispositions.csv"
    summary_path = output_dir / "2024_summary.csv"

    assert monthly_path.exists()
    assert dispositions_path.exists()
    assert summary_path.exists()

    with open(monthly_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["lot_id"] == "lot-1"
        assert rows[0]["month"] == "8"

    with open(dispositions_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["disposition_id"] == "lot-1-sell-1"

    with open(summary_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["total_investment_expense"] == "2.18"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_csv_export.py -v`
Expected: FAIL

- [ ] **Step 3: Implement CSV export**

`fbtc_taxgrinder/export/csv_export.py`:
```python
from __future__ import annotations

import csv
from pathlib import Path

from fbtc_taxgrinder.models import YearResult


def export_year_csv(year_result: YearResult, output_dir: Path) -> None:
    """Export year results to three CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    year = year_result.year

    # Monthly breakdown
    monthly_path = output_dir / f"{year}_monthly.csv"
    with open(monthly_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "lot_id", "month", "days_held", "days_in_month", "shares",
            "total_btc_sold", "cost_basis_of_sold", "total_expense",
            "gain_loss", "adj_btc", "adj_basis",
        ])
        for lot_id, results in sorted(year_result.lot_results.items()):
            for mr in results:
                writer.writerow([
                    lot_id, mr.month, mr.days_held, mr.days_in_month,
                    mr.shares, mr.total_btc_sold, mr.cost_basis_of_sold,
                    mr.total_expense, mr.gain_loss, mr.adj_btc, mr.adj_basis,
                ])

    # Dispositions
    disp_path = output_dir / f"{year}_dispositions.csv"
    with open(disp_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "lot_id", "disposition_id", "date_sold", "shares_sold",
            "proceeds", "disposed_btc", "disposed_basis", "gain_loss",
        ])
        for d in year_result.dispositions:
            writer.writerow([
                d.lot_id, d.disposition_id, d.date_sold.isoformat(),
                d.shares_sold, d.proceeds, d.disposed_btc,
                d.disposed_basis, d.gain_loss,
            ])

    # Annual summary
    summary_path = output_dir / f"{year}_summary.csv"
    with open(summary_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "year", "total_investment_expense", "total_reportable_gain",
            "total_cost_basis_of_expense",
        ])
        writer.writerow([
            year, year_result.total_investment_expense,
            year_result.total_reportable_gain,
            year_result.total_cost_basis_of_expense,
        ])
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_csv_export.py -v`
Expected: All PASS

- [ ] **Step 5: Check coverage**

Run: `pytest tests/test_csv_export.py --cov=fbtc_taxgrinder.export --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage. Add tests for uncovered branches.

- [ ] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/export/csv_export.py tests/test_csv_export.py
git commit -m "feat: implement CSV export for monthly, dispositions, and summary"
```

---

## Task 11: CLI Commands

**Files:**
- Modify: `fbtc_taxgrinder/cli/commands.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write failing test for import-proceeds command**

`tests/test_cli.py`:
```python
from click.testing import CliRunner
from fbtc_taxgrinder.cli.commands import cli
from fbtc_taxgrinder.db import proceeds


def test_import_proceeds_from_file(tmp_path, data_dir):
    """Test import-proceeds --file with a mock PDF (integration test)."""
    # This test requires a real PDF or a mock. For now, test the CLI wiring
    # with a missing file to verify the command exists and validates input.
    runner = CliRunner()
    result = runner.invoke(cli, [
        "import-proceeds", "--file", "/nonexistent.pdf",
        "--data-dir", str(data_dir),
    ])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "error" in result.output.lower()


def test_status_empty(data_dir):
    runner = CliRunner()
    result = runner.invoke(cli, ["status", "--data-dir", str(data_dir)])
    assert result.exit_code == 0
    assert "No lots" in result.output or "0 lots" in result.output


def test_compute_missing_proceeds(data_dir):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "compute", "--year", "2024", "--data-dir", str(data_dir),
    ])
    assert result.exit_code != 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_cli.py -v`
Expected: FAIL

- [ ] **Step 3: Implement all CLI commands**

`fbtc_taxgrinder/cli/commands.py`:
```python
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import click

from fbtc_taxgrinder.db import lots as lots_db
from fbtc_taxgrinder.db import proceeds as proceeds_db
from fbtc_taxgrinder.db import results as results_db
from fbtc_taxgrinder.db import state as state_db
from fbtc_taxgrinder.engine.compute import compute_year
from fbtc_taxgrinder.engine.matching import match_sell_to_lot
from fbtc_taxgrinder.export.csv_export import export_year_csv
from fbtc_taxgrinder.models import Lot, LotEvent, LotState
from fbtc_taxgrinder.parsers.etrade import parse_etrade_csv
from fbtc_taxgrinder.parsers.fidelity_pdf import parse_fidelity_pdf


def _data_dir(ctx: click.Context) -> Path:
    return ctx.obj["data_dir"]


@click.group()
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=Path("data"),
    help="Path to data directory.",
)
@click.pass_context
def cli(ctx, data_dir: Path):
    """FBTC Tax Lot Grinder — compute IRS-reportable WHFIT tax lots."""
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "proceeds").mkdir(exist_ok=True)
    (data_dir / "results").mkdir(exist_ok=True)
    (data_dir / "state").mkdir(exist_ok=True)


@cli.command("import-proceeds")
@click.option("--url", help="URL to Fidelity WHFIT PDF.")
@click.option("--file", "file_path", help="Local path to Fidelity WHFIT PDF.")
@click.pass_context
def import_proceeds(ctx, url: str | None, file_path: str | None):
    """Import Fidelity Gross Proceeds data from PDF."""
    if not url and not file_path:
        raise click.UsageError("Provide --url or --file.")

    source = url or file_path
    if file_path and not Path(file_path).exists():
        raise click.ClickException(f"File not found: {file_path}")

    click.echo(f"Parsing proceeds from {source}...")
    yp = parse_fidelity_pdf(source)

    # Detect year from data
    if not yp.daily:
        raise click.ClickException("No data found in PDF.")
    first_date = min(yp.daily.keys())
    year = first_date.year

    dd = _data_dir(ctx)
    existing = proceeds_db.load(dd, year)
    if existing is not None:
        click.echo(f"Proceeds for {year} already imported ({existing.source}). Skipping.")
        return

    proceeds_db.save(dd, year, yp)
    click.echo(
        f"Imported {year} proceeds: {len(yp.daily)} daily rows, "
        f"{len(yp.monthly)} month-end rows."
    )


@cli.command("import-trades")
@click.option("--file", "file_path", required=True, help="Path to ETrade CSV file.")
@click.pass_context
def import_trades(ctx, file_path: str):
    """Import FBTC trades (buys and sells) from ETrade CSV."""
    if not Path(file_path).exists():
        raise click.ClickException(f"File not found: {file_path}")

    dd = _data_dir(ctx)
    parsed = parse_etrade_csv(file_path)
    existing_lots = lots_db.load(dd)

    # Track existing lots by (date, shares, price) for idempotency
    existing_keys = {
        (lot.purchase_date, lot.original_shares, lot.price_per_share)
        for lot in existing_lots
    }

    next_id = len(existing_lots) + 1
    new_lots = 0
    source_name = Path(file_path).name

    for buy in parsed["buys"]:
        key = (buy["date"], buy["shares"], buy["price_per_share"])
        if key in existing_keys:
            continue

        # Look up btc_per_share on purchase date
        year = buy["date"].year
        yp = proceeds_db.load(dd, year)
        if yp is None:
            raise click.ClickException(
                f"Proceeds for {year} not imported. "
                f"Run 'import-proceeds' first."
            )
        btc = yp.daily.get(buy["date"])
        if btc is None:
            raise click.ClickException(
                f"No BTC-per-share data for {buy['date'].isoformat()} in {year} proceeds."
            )

        lot = Lot(
            id=f"lot-{next_id}",
            purchase_date=buy["date"],
            original_shares=buy["shares"],
            price_per_share=buy["price_per_share"],
            total_cost=buy["total_cost"],
            btc_per_share_on_purchase=btc,
            source_file=source_name,
            events=[],
        )
        existing_lots.append(lot)
        existing_keys.add(key)
        next_id += 1
        new_lots += 1

    # Process sells
    new_sells = 0
    for sell in parsed["sells"]:
        matched_lot = match_sell_to_lot(
            existing_lots,
            sell_shares=sell["shares"],
            sell_date=sell["date"],
        )
        # Check idempotency: skip if this sell already recorded
        already_exists = any(
            e.date == sell["date"] and e.shares == sell["shares"]
            for e in matched_lot.events
        )
        if already_exists:
            continue

        sell_count = sum(1 for e in matched_lot.events if e.type == "sell")
        matched_lot.events.append(LotEvent(
            type="sell",
            date=sell["date"],
            shares=sell["shares"],
            price_per_share=sell["price_per_share"],
            proceeds=sell["proceeds"],
            disposition_id=f"{matched_lot.id}-sell-{sell_count + 1}",
        ))
        new_sells += 1

    lots_db.save(dd, existing_lots)
    click.echo(f"Imported {new_lots} new lots, {new_sells} new sells.")


@cli.command()
@click.option("--year", required=True, type=int, help="Tax year to compute.")
@click.option("--force", is_flag=True, help="Recompute even if results exist.")
@click.pass_context
def compute(ctx, year: int, force: bool):
    """Compute tax lots for a given year."""
    dd = _data_dir(ctx)

    # Check for existing results
    if not force and results_db.load(dd, year) is not None:
        click.echo(f"Results for {year} already computed. Use --force to recompute.")
        return

    # Load proceeds
    yp = proceeds_db.load(dd, year)
    if yp is None:
        raise click.ClickException(
            f"No proceeds data for {year}. Run 'import-proceeds' first."
        )

    # Load lots
    all_lots = lots_db.load(dd)
    if not all_lots:
        raise click.ClickException("No lots found. Run 'import-trades' first.")

    # Load prior state chain
    # For each lot, walk from purchase year to target year
    prior = None
    if year > min(lot.purchase_date.year for lot in all_lots):
        prior = state_db.load(dd, year - 1)

    result = compute_year(
        lots=all_lots,
        proceeds=yp,
        prior_state=prior,
        year=year,
    )

    # Save results and year-end state (end_states computed by engine)
    results_db.save(dd, result)
    state_db.save(dd, year, result.end_states)

    click.echo(
        f"Computed {year}: "
        f"expense=${result.total_investment_expense:.2f}, "
        f"gain=${result.total_reportable_gain:.2f}, "
        f"dispositions={len(result.dispositions)}"
    )


@cli.command()
@click.option("--year", required=True, type=int)
@click.option("--format", "fmt", default="csv", type=click.Choice(["csv"]))
@click.option("--output", "output_dir", required=True, type=click.Path(path_type=Path))
@click.pass_context
def export(ctx, year: int, fmt: str, output_dir: Path):
    """Export computed results."""
    dd = _data_dir(ctx)
    yr = results_db.load(dd, year)
    if yr is None:
        raise click.ClickException(f"No results for {year}. Run 'compute' first.")
    export_year_csv(yr, output_dir)
    click.echo(f"Exported {year} results to {output_dir}/")


@cli.command("lots")
@click.pass_context
def list_lots(ctx):
    """List all lots and their events."""
    dd = _data_dir(ctx)
    all_lots = lots_db.load(dd)
    if not all_lots:
        click.echo("No lots found.")
        return
    for lot in all_lots:
        click.echo(
            f"{lot.id}: {lot.purchase_date} | {lot.original_shares} shares "
            f"@ ${lot.price_per_share} | cost=${lot.total_cost}"
        )
        for e in lot.events:
            click.echo(
                f"  {e.type}: {e.date} | {e.shares} shares "
                f"@ ${e.price_per_share} | proceeds=${e.proceeds}"
            )


@cli.command()
@click.pass_context
def status(ctx):
    """Show what data is imported and computed."""
    dd = _data_dir(ctx)
    all_lots = lots_db.load(dd)
    click.echo(f"Lots: {len(all_lots)} lots")
    sells = sum(len(lot.events) for lot in all_lots)
    click.echo(f"Sell events: {sells}")

    # Check proceeds years
    proceeds_dir = dd / "proceeds"
    if proceeds_dir.exists():
        years = sorted(int(f.stem) for f in proceeds_dir.glob("*.json"))
        click.echo(f"Proceeds: {', '.join(str(y) for y in years) if years else 'none'}")
    else:
        click.echo("Proceeds: none")

    # Check computed years
    results_dir = dd / "results"
    if results_dir.exists():
        years = sorted(int(f.stem) for f in results_dir.glob("*.json"))
        click.echo(f"Computed: {', '.join(str(y) for y in years) if years else 'none'}")
    else:
        click.echo("Computed: none")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_cli.py -v`
Expected: All PASS

- [ ] **Step 5: Check coverage**

Run: `pytest tests/test_cli.py --cov=fbtc_taxgrinder.cli --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ coverage. Add tests for uncovered CLI paths (error cases, edge cases).

- [ ] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/cli/commands.py tests/test_cli.py
git commit -m "feat: implement CLI commands — import-proceeds, import-trades, compute, export, lots, status"
```

---

## Task 12: Spreadsheet Validation Tests

Cross-reference computed output against known spreadsheet values for lots 1-9 (unaffected by proration bug).

**Files:**
- Create: `tests/test_validation.py`

- [ ] **Step 1: Write validation test**

`tests/test_validation.py`:
```python
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

        assert btc_diff < Decimal("1E-10"), (
            f"{lot_id} adj_btc: expected {expected['adj_btc']}, "
            f"got {last_month.adj_btc}, diff={btc_diff}"
        )
        assert basis_diff < Decimal("0.000001"), (
            f"{lot_id} adj_basis: expected {expected['adj_basis']}, "
            f"got {last_month.adj_basis}, diff={basis_diff}"
        )
```

- [ ] **Step 2: Add lots 10-15 proration bug delta test**

Add to `tests/test_validation.py`:
```python
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
```

- [ ] **Step 3: Run validation tests**

Run: `pytest tests/test_validation.py -v`
Expected: PASS for both tests. Lots 1-9 match spreadsheet; lots 10-15 differ from buggy values.

- [ ] **Step 3: Commit**

```bash
git add tests/test_validation.py
git commit -m "test: add spreadsheet cross-reference validation for lots 1-9"
```

---

## Task 13: End-to-End Integration Test

Verify the full workflow: import proceeds, import trades, compute, export.

**Files:**
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Write E2E test**

Add to `tests/test_cli.py`:
```python
import csv
from pathlib import Path
from decimal import Decimal
from datetime import date
from click.testing import CliRunner
from fbtc_taxgrinder.cli.commands import cli
from fbtc_taxgrinder.db import proceeds as proceeds_db
from fbtc_taxgrinder.models import MonthProceeds, YearProceeds


def test_e2e_workflow(data_dir, tmp_path):
    """Full workflow: seed proceeds, import trades, compute, export."""
    runner = CliRunner()

    # Manually seed proceeds (skip PDF parsing for this test)
    yp = YearProceeds(
        daily={date(2024, 1, 25): Decimal("0.00087448")},
        monthly={
            date(2024, 8, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        },
        source="test",
    )
    proceeds_db.save(data_dir, 2024, yp)

    # Create a minimal ETrade CSV
    csv_path = tmp_path / "trades.csv"
    with open(csv_path, "w") as f:
        f.write("Trade Date,Order Type,Security,Cusip,Transaction Description,Quantity,Executed Price,Commission,Net Amount\n")
        f.write('1/25/2024,Buy,FBTC,315948109,"FIDELITY WISE ORIGIN BITCOIN",204,34.81,0.0000,7101.24\n')

    # Import trades
    result = runner.invoke(cli, [
        "import-trades", "--file", str(csv_path),
        "--data-dir", str(data_dir),
    ])
    assert result.exit_code == 0, result.output
    assert "1 new lots" in result.output

    # Compute
    result = runner.invoke(cli, [
        "compute", "--year", "2024",
        "--data-dir", str(data_dir),
    ])
    assert result.exit_code == 0, result.output

    # Export
    output_dir = tmp_path / "output"
    result = runner.invoke(cli, [
        "export", "--year", "2024", "--format", "csv",
        "--output", str(output_dir),
        "--data-dir", str(data_dir),
    ])
    assert result.exit_code == 0, result.output
    assert (output_dir / "2024_monthly.csv").exists()
    assert (output_dir / "2024_summary.csv").exists()

    # Verify skip on re-compute
    result = runner.invoke(cli, [
        "compute", "--year", "2024",
        "--data-dir", str(data_dir),
    ])
    assert "already computed" in result.output

    # Verify --force recomputes
    result = runner.invoke(cli, [
        "compute", "--year", "2024", "--force",
        "--data-dir", str(data_dir),
    ])
    assert result.exit_code == 0
```

- [ ] **Step 2: Run E2E test**

Run: `pytest tests/test_cli.py::test_e2e_workflow -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/test_cli.py
git commit -m "test: add end-to-end CLI integration test"
```

---

## Task 14: Run Full Test Suite, Coverage Gate, and Code Quality

- [ ] **Step 1: Run all tests**

Run: `pytest tests/ -v`
Expected: All PASS

- [ ] **Step 2: Run full coverage report**

Run: `pytest tests/ --cov=fbtc_taxgrinder --cov-report=term-missing --cov-fail-under=90`
Expected: 90%+ overall coverage. If below, identify uncovered lines and add tests.

- [ ] **Step 3: Check for any uncovered error paths**

Review the `term-missing` output. Common gaps:
- Error handling in CLI commands (missing file, missing proceeds, chain validation errors)
- Edge cases in parsers (malformed input)
- Fully liquidated lot behavior in compute_year

Add targeted tests for any uncovered lines.

- [ ] **Step 4: Run type checking (optional but recommended)**

Run: `python -m py_compile fbtc_taxgrinder/models.py fbtc_taxgrinder/engine/compute.py fbtc_taxgrinder/engine/matching.py fbtc_taxgrinder/db/lots.py fbtc_taxgrinder/db/proceeds.py fbtc_taxgrinder/db/results.py fbtc_taxgrinder/db/state.py fbtc_taxgrinder/parsers/etrade.py fbtc_taxgrinder/parsers/fidelity_pdf.py fbtc_taxgrinder/export/csv_export.py fbtc_taxgrinder/cli/commands.py`
Expected: No syntax errors.

- [ ] **Step 5: Fix any failures**

Debug and fix. Re-run until green with 90%+ coverage.

- [ ] **Step 6: Final commit**

```bash
git add -A
git commit -m "fix: resolve remaining test issues, achieve 90%+ coverage"
```

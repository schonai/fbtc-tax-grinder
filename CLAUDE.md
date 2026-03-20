## Project Overview

FBTC Tax Grinder is a Python CLI that computes IRS-reportable WHFIT tax lots for Fidelity Bitcoin Fund (FBTC) shareholders. It implements Fidelity's official 2025 grantor trust 6-step gain/loss calculation for each lot on a monthly basis.

## Commands

```bash
# Install (editable mode with dev deps)
pip3 install -e ".[dev]"

# Run all tests
pytest

# Run tests with coverage (must be ≥90%)
pytest --cov=fbtc_taxgrinder --cov-report=term-missing --cov-fail-under=90

# Run a single test file or test
pytest tests/test_compute.py -v
pytest tests/test_compute.py::test_name -v

# CLI entry point
fbtc-taxgrinder --help
```

## Architecture

**Data flow:** Fidelity PDF → `import-proceeds` → JSON state → `import-trades` (ETrade CSV) → `compute` → `export` (3 CSVs)

### Key modules

- **`models.py`** — Core dataclasses: `Lot`, `LotEvent`, `YearProceeds`, `YearResult`, `Disposition`, `ExpenseResult`, `LotState`. All financial values use `Decimal` for precision.
- **`parsers/`** — `fidelity_pdf.py` extracts daily BTC/share and monthly expense data from WHFIT PDFs; `etrade.py` parses trade CSVs into buy/sell lists.
- **`engine/compute.py`** — Implements the 6-step monthly calculation per lot: BTC ownership → BTC sold (prorated by days held) → cost basis → expense → gain/loss → updated state. Handles multi-sell months by splitting into phases.
- **`engine/matching.py`** — Matches sell transactions to lots with ambiguity detection.
- **`db/`** — JSON persistence layer: `lots.json`, `proceeds/{year}.json`, `results/{year}.json`, `state/{year}.json`. Custom codec for `Decimal`/`date` serialization.
- **`cli/commands.py`** — Six Click commands: `import-proceeds`, `import-trades`, `compute`, `export`, `lots`, `status`.
- **`export/csv_export.py`** — Generates monthly, dispositions, and summary CSVs.

### State chaining

Year-end `LotState` snapshots (adjusted BTC, adjusted basis, remaining shares) are saved and used as prior state for the next year's computation.

## Reference Documents

- [FBTC 2025 Grantor Trust Tax Reporting Statement](docs/fbtc-2025-grantor-trust-tax-reporting.md) — Fidelity's WHFIT tax reporting guidance including the 6-step gain/loss and basis calculation example for FBTC shareholders.

## Testing

- Prefer mocks over filesystem/expensive resources in unit tests
- Reserve real filesystem, databases, and network for integration tests only
- Every task must achieve 90%+ test coverage on files it creates or modifies
- Verify with: `pytest --cov=fbtc_taxgrinder --cov-report=term-missing --cov-fail-under=90`

# FBTC Tax Grinder

[![CI](https://github.com/schonai/fbtc-tax-grinder/actions/workflows/ci.yml/badge.svg)](https://github.com/schonai/fbtc-tax-grinder/actions/workflows/ci.yml)

Python CLI to compute WHFIT tax lots and gain/loss for Fidelity Bitcoin Fund (FBTC) shareholders.

Implements Fidelity's official 2025 grantor trust 6-step gain/loss and basis calculation on a per-lot, per-month basis. Ingests data from Fidelity WHFIT PDFs and ETrade trade CSVs, then exports IRS-reportable results.

## Why?

FBTC is structured as a grantor trust, which means shareholders are taxed directly on the trust's Bitcoin activity — not just on share sales. Fidelity publishes a WHFIT tax reporting statement each year with daily BTC-per-share data and monthly expense figures, but they don't compute per-lot results for you. This tool does that: it takes your trade history and Fidelity's published data, then calculates the gain/loss and expense figures you need for your tax return.

## Quick start

```bash
pip3 install -e ".[dev]"

fbtc-taxgrinder --project ./my-taxes import-proceeds --url <fidelity-whfit-pdf-url>
fbtc-taxgrinder --project ./my-taxes import-trades --file etrade-trades.csv
fbtc-taxgrinder --project ./my-taxes compute --year 2025
fbtc-taxgrinder --project ./my-taxes export --year 2025
```

Output lands in `./my-taxes/output/` as three CSVs (monthly breakdown, dispositions, and annual summary).

## Installation

Requires Python 3.12+.

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -e ".[dev]"
```

## Usage

All commands require `--project PATH` to specify the project directory. This directory holds all imported data, computed results, and exported CSVs.

### 1. Import Fidelity gross proceeds data

From a local PDF:

```bash
fbtc-taxgrinder --project ./my-taxes import-proceeds --file path/to/fidelity-whfit-2025.pdf
```

From a URL:

```bash
fbtc-taxgrinder --project ./my-taxes import-proceeds --url <pdf-url>
```

Fidelity publishes WHFIT annual statements for each tax year:

| Tax Year | PDF                                                                                                                                                                   |
|----------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| 2024     | [FBTC WHFIT Annual Statement 2024](https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/research/1185828.1.0-FBTCWHFITAnnualStmt2024.pdf)               |
| 2025     | [FBTC WHFIT Annual Statement 2025](https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/research/1185828.2.0_WHFIT%20Annual%20Stmt%20UDA_FBTC_2025.pdf) |

### 2. Import trades from ETrade

```bash
fbtc-taxgrinder --project ./my-taxes import-trades --file path/to/etrade-trades.csv
```

### 3. Compute tax lots

```bash
fbtc-taxgrinder --project ./my-taxes compute --year 2025
```

Use `--force` to recompute if results already exist. Two mutually exclusive flags control how buy and sell months are handled:

- `--full-month` (default) — uses full-month granularity for buy and sell months, matching Fidelity's 1099 values.
- `--prorate` — prorates buy and sell months by actual days held, as described in the WHFIT tax reporting document example.

### 4. Export results

```bash
fbtc-taxgrinder --project ./my-taxes export --year 2025
```

Generates three CSV files in `<project>/output/`:

| File                     | Contents                                                 |
|--------------------------|----------------------------------------------------------|
| `2025_monthly.csv`       | Monthly breakdown per lot (days held, expenses, gains)   |
| `2025_dispositions.csv`  | Individual sell transactions with gain/loss              |
| `2025_summary.csv`       | Annual totals                                            |

### Other commands

```bash
fbtc-taxgrinder --project ./my-taxes lots      # List all lots and sell events
fbtc-taxgrinder --project ./my-taxes status    # Show import/compute status
```

## How it works

```text
Fidelity PDF ──> import-proceeds ──> JSON state ──> compute ──> export ──> CSVs
ETrade CSV ───> import-trades ────────┘
```

The tool follows Fidelity's 6-step WHFIT calculation for each lot in each month:

1. **Identify BTC ownership** — adjusted BTC per share after prior sales
2. **Calculate BTC sold** — prorated by days held in the month
3. **Cost basis** — portion of adjusted basis attributable to BTC sold
4. **Investment expense** — prorated monthly USD proceeds per share
5. **Gain/Loss** — expense minus cost basis
6. **Update state** — carry forward adjusted BTC and basis to the next period

Year-end states chain into the following year, enabling multi-year tracking.

## Note on holding period calculation

Fidelity's WHFIT tax reporting document shows an example where buy and sell months are prorated by actual days held (e.g., 21 out of 30 days for a purchase on 9/9, or phase-splitting around a mid-month sell). However, comparing against actual 1099 values shows that Fidelity uses full-month granularity: shares held at month-end get the full month's expense regardless of buy date, and shares sold before month-end get zero expense for that month.

This tool defaults to full-month granularity (`--full-month`) to match the 1099. The `--prorate` flag is available to use the documented proration method instead.

## Known limitations

**Penny-level rounding discrepancy:** This tool maintains full decimal precision throughout all calculation steps and rounds to cents only at CSV export time. Fidelity's published WHFIT example shows a total reportable gain of -$8.65, but neither full-precision-then-round nor intermediate rounding exactly reproduces that figure. The exact internal rounding strategy Fidelity uses cannot be determined from published data. As a result, computed values may differ from Fidelity's by 1-2 cents on individual line items.

## Development

```bash
# Run all tests
pytest

# Run tests with coverage (must be >= 90%)
pytest --cov=fbtc_taxgrinder --cov-report=term-missing --cov-fail-under=90

# Run a single test
pytest tests/test_compute.py::test_name -v
```

## License

[MIT](LICENSE)

## Disclaimer

This tool is provided for informational and educational purposes only. It is not financial, tax, or legal advice. The authors make no guarantees about the accuracy or completeness of the calculations. Tax laws are complex and subject to change — consult a qualified tax professional before making any decisions based on this tool's output. Use at your own risk.

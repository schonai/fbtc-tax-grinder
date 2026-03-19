# FBTC Tax Grinder

Python CLI to compute WHFIT tax lots and gain/loss for Fidelity Bitcoin Fund (FBTC) shareholders.

Implements Fidelity's official 2025 grantor trust 6-step gain/loss and basis calculation on a per-lot, per-month basis. Ingests data from Fidelity WHFIT PDFs and ETrade trade CSVs, then exports IRS-reportable results.

## Installation

Requires Python 3.12+.

```bash
python3 -m venv venv
source venv/bin/activate
pip3 install -e ".[dev]"
```

## Usage

### 1. Import Fidelity gross proceeds data

From a local PDF:

```bash
fbtc-taxgrinder import-proceeds --file path/to/fidelity-whfit-2025.pdf
```

From a URL:

```bash
fbtc-taxgrinder import-proceeds --url https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/research/1185828.2.0_WHFIT%20Annual%20Stmt%20UDA_FBTC_2025.pdf
```

Fidelity publishes WHFIT annual statements for each tax year:

| Tax Year | PDF URL |
|----------|---------|
| 2024 | https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/research/1185828.1.0-FBTCWHFITAnnualStmt2024.pdf |
| 2025 | https://www.fidelity.com/bin-public/060_www_fidelity_com/documents/research/1185828.2.0_WHFIT%20Annual%20Stmt%20UDA_FBTC_2025.pdf |

### 2. Import trades from ETrade

```bash
fbtc-taxgrinder import-trades --file path/to/etrade-trades.csv
```

### 3. Compute tax lots

```bash
fbtc-taxgrinder compute --year 2025
```

Use `--force` to recompute if results already exist. Two mutually exclusive flags control how buy and sell months are handled:

- `--full-month` (default) — uses full-month granularity for buy and sell months, matching Fidelity's 1099 values.
- `--prorate` — prorates buy and sell months by actual days held, as described in the WHFIT tax reporting document example.

### 4. Export results

```bash
fbtc-taxgrinder export --year 2025 --output ./output
```

Generates three CSV files:
- `2025_monthly.csv` — Monthly breakdown per lot (days held, expenses, gains)
- `2025_dispositions.csv` — Individual sell transactions with gain/loss
- `2025_summary.csv` — Annual totals

### Other commands

```bash
fbtc-taxgrinder lots      # List all lots and sell events
fbtc-taxgrinder status    # Show import/compute status
```

All commands accept `--data-dir PATH` to specify the data directory (defaults to `./data`).

## How it works

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

## Disclaimer

This tool is provided for informational and educational purposes only. It is not financial, tax, or legal advice. The authors make no guarantees about the accuracy or completeness of the calculations. Tax laws are complex and subject to change — consult a qualified tax professional before making any decisions based on this tool's output. Use at your own risk.

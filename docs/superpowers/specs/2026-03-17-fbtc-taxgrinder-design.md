# fbtc-taxgrinder Design Spec

## Overview

Python CLI tool to compute IRS-reportable tax lots for FBTC (Fidelity Wise Origin Bitcoin Fund), a grantor trust (WHFIT) under Treas. Reg. Sec. 1.671-5.

FBTC holds only Bitcoin. Its only taxable event is the daily sale of a tiny amount of BTC per share to cover trust management expenses. Each shareholder must compute, per tax lot, the resulting gain/loss and adjusted cost basis, chaining results forward month over month and year over year.

This tool replaces a Google Sheets implementation that has grown unwieldy and contains a known proration bug.

---

## Data Model

### Lots (`data/lots.json`)

Each lot represents an FBTC purchase with an optional history of sell events.

```json
[
  {
    "id": "lot-1",
    "purchase_date": "2024-01-25",
    "original_shares": "204",
    "price_per_share": "34.81",
    "total_cost": "7101.24",
    "btc_per_share_on_purchase": "0.00087448",
    "source_file": "tradesdownload.csv.xls",
    "events": [
      {
        "type": "sell",
        "date": "2025-12-23",
        "shares": "14",
        "price_per_share": "76.2201",
        "proceeds": "1067.08",
        "disposition_id": "lot-1-sell-1"
      }
    ]
  }
]
```

- Lot IDs are stable and human-readable (`lot-1`, `lot-2`, etc.)
- Sell events are attached to the parent lot, not separate entities
- The lot's share count at any point in time is derived from `original_shares` minus cumulative sells up to that date
- All numeric values stored as strings to preserve Decimal precision

### Proceeds (`data/proceeds/{year}.json`)

One file per year, containing daily BTC-per-share and month-end expense data, parsed from Fidelity's annual WHFIT PDF.

```json
{
  "daily": {
    "2024-01-11": { "btc_per_share": "0.00087448" },
    "2024-01-12": { "btc_per_share": "0.00087448" }
  },
  "monthly": {
    "2024-08-31": {
      "btc_sold_per_share": "0.00000018",
      "proceeds_per_share_usd": "0.01070327"
    }
  },
  "source": "1185828.1.0-FBTCWHFITAnnualStmt2024.pdf"
}
```

### Results (`data/results/{year}.json`)

Per-lot per-month computation output for a given year.

```json
{
  "lot-1": [
    {
      "month": 8,
      "days_held": "31",
      "days_in_month": "31",
      "shares": "204",
      "total_btc_sold": "0.00003672",
      "cost_basis_of_sold": "1.461695179",
      "total_expense": "2.18346708",
      "gain_loss": "0.7217719012",
      "adj_btc": "0.17835720",
      "adj_basis": "7099.778305"
    }
  ],
  "dispositions": [
    {
      "lot_id": "lot-1",
      "disposition_id": "lot-1-sell-1",
      "date_sold": "2025-12-23",
      "shares_sold": "14",
      "proceeds": "1067.08",
      "disposed_btc": "0.01221234",
      "disposed_basis": "487.12",
      "gain_loss": "579.96"
    }
  ]
}
```

### Year-End State (`data/state/{year}.json`)

Per-lot year-end `adj_btc`, `adj_basis`, and current share count, used to seed the next year's computation.

```json
{
  "lot-1": {
    "adj_btc": "0.17821032",
    "adj_basis": "7093.928514",
    "shares": "204"
  }
}
```

---

## Tax Computation Logic (Fidelity's 6-Step Method)

All computations are per lot, per month, chained forward. All arithmetic uses `Decimal` (no floats). Full precision is carried in all intermediate values; rounding to 2 decimal places (USD) or 8 decimal places (BTC) is applied only at export/display time.

### Inputs per lot

- `purchase_date`: date of purchase
- `shares`: number of shares (may change over time due to sells)
- `price_per_share`: execution price
- `total_cost`: shares x price (original cost basis)
- `btc_per_share_on_purchase_date`: looked up from proceeds daily data

### Monthly computation per lot

For each month M after the purchase month:

#### State carried from previous month (or initial values)

- `adj_btc`: adjusted BTC held (initially = `btc_per_share_on_purchase_date x shares`)
- `adj_basis`: adjusted cost basis in USD (initially = `total_cost`)

#### Step 1: Days held proration

- First month held (purchase month): `days_held = month_end_date - purchase_date` (purchase date is NOT counted; e.g., bought Sep 9 -> Sep 30 - Sep 9 = 21 days)
- If first month `days_held = 0` (purchased on last day of month): the lot's first active month is the following month
- Subsequent months: `days_held = days_in_month` (full month)
- If `purchase_date > month_end_date`: lot not yet active, skip

#### Step 2: BTC sold from this lot

```
btc_sold_per_share_this_month = (days_held / days_in_month) x monthly_btc_sold_per_share
total_btc_sold = btc_sold_per_share_this_month x shares
```

#### Step 3: Cost basis of BTC sold

```
cost_basis_of_sold = (total_btc_sold / adj_btc) x original_total_cost
```

IMPORTANT: Uses the original purchase price (`total_cost`), NOT the running adjusted basis.

#### Step 4: Investment expense

```
expense_per_share = (days_held / days_in_month) x monthly_proceeds_per_share
total_expense = expense_per_share x shares
```

#### Step 5: Gain or Loss

```
gain_loss = total_expense - cost_basis_of_sold
```

#### Step 6: Adjusted values carried forward

```
adj_btc_new = adj_btc - total_btc_sold
adj_basis_new = adj_basis - cost_basis_of_sold
```

#### Role of `adj_basis`

`adj_basis` tracks the running adjusted cost basis for disposition purposes only. It is NOT used in Step 3 (which always uses `original_total_cost`). When shares are sold, `adj_basis` determines the disposed cost basis and therefore the capital gain/loss on the sale.

### Sell event processing

When a sell occurs mid-month, the computation runs sequentially through three phases:

**Phase 1 — Pre-sell expense computation:**
Run Steps 1-6 for the period from month start to sell date.
- `days_held = sell_date - month_start` (or `sell_date - purchase_date` if purchase month)
- Use pre-sell share count
- Update `adj_btc` and `adj_basis` with the results

**Phase 2 — Disposition:**
At the sell date, compute proportional disposal from the updated state:

```
disposed_btc = adj_btc x (shares_sold / current_shares)
disposed_basis = adj_basis x (shares_sold / current_shares)
disposition_gain_loss = proceeds - disposed_basis
```

Reduce `adj_btc` and `adj_basis` by the disposed amounts. Reduce share count.

**Phase 3 — Post-sell expense computation:**
Run Steps 1-6 for the remainder of the month.
- `days_held = month_end - sell_date`
- Use post-sell share count
- Update `adj_btc` and `adj_basis` with the results

The month's total expense `gain_loss` is the sum of Phase 1 and Phase 3 gain/loss values. The disposition gain/loss is recorded separately.

**Multiple sells in the same month:** If two sells occur in one month, the month is split into three expense periods with a disposition between each. The phases chain sequentially: expense -> dispose -> expense -> dispose -> expense.

**Sell that fully liquidates a lot:** After disposition, share count is 0. Phase 3 is skipped (no remaining shares). The lot is marked as fully liquidated and excluded from future months.

### Sell matching logic

When importing sells from the ETrade CSV, the tool matches each sell to an existing lot:

1. Find all lots with remaining shares >= sell quantity
2. If exactly one candidate: match
3. If multiple candidates: bail with error listing the ambiguous lots
4. If no candidates: bail with error

No automatic cost basis method (FIFO, etc.) is applied. Ambiguous sells must be resolved by the user.

### Year-end rollover

- December's `adj_btc`, `adj_basis`, and current share count become January's starting values
- New lots purchased in the new year start fresh
- Prior year state is loaded automatically; missing intermediate years produce an error

### Prior state chain validation

For each lot, every year from its purchase year through the target year must have computed results. Example: a lot from 2024 computing 2026 requires both 2024 and 2025 results.

Error message: "Lot lot-1 (purchased 2024-01-25) requires 2024 results before computing 2025"

### Annual summary

- `total_investment_expense = sum(total_expense)` across all lots and months
- `total_reportable_gain = sum(gain_loss)` across all lots and months
- `total_cost_basis_of_expense = total_investment_expense - total_reportable_gain` (equivalently, this equals `sum(cost_basis_of_sold)` across all lots/months — use as cross-check)
- Disposition gains/losses reported separately

---

## Known Bug in Current Spreadsheet

First-month days-held proration is missing for lots purchased within the active month range. The `days_held` is hardcoded to the full month instead of being prorated from the purchase date.

Affected lots (2024 data). Note: "Row" refers to spreadsheet rows; "Lot ID" is the tool's ID (lot-10 through lot-15 in the validation table below):

| Lot ID | Spreadsheet Row | Purchase Date | First Active Month | days_held (buggy) | days_held (correct) |
|--------|----------------|--------------|-------------------|-------------------|---------------------|
| lot-10 | Row 12 | 2024-08-19 | Aug | 31 | 12 |
| lot-11 | Row 13 | 2024-08-19 | Aug | 31 | 12 |
| lot-12 | Row 14 | 2024-09-09 | Sep | 30 | 21 |
| lot-13 | Row 15 | 2024-09-09 | Sep | 30 | 21 |
| lot-14 | Row 16 | 2024-10-17 | Oct | 31 | 14 |
| lot-15 | Row 17 | 2024-11-05 | Nov | 30 | 25 |

The Python implementation uses the correct prorated formula for all lots.

---

## Parsers

### ETrade CSV Parser (`parsers/etrade.py`)

- Reads `.csv.xls` files (CSV format despite extension)
- Filters rows where `Security == "FBTC"`
- Separates buys and sells by `Order Type`
- Processes all transactions chronologically
- For buys: creates new lot entries, looks up `btc_per_share_on_purchase` from proceeds daily data
- For sells: matches to existing lots (see sell matching logic above)
- Errors if proceeds not yet imported for the relevant year
- Idempotent: re-importing the same file skips existing lots (matched by date + shares + price)

### Fidelity PDF Parser (`parsers/fidelity_pdf.py`)

- Accepts URL or local file path
- Downloads PDF to temp file if URL provided
- Uses `pdfplumber` to extract tables
- Parses daily rows: date -> btc_per_share (365 rows)
- Parses month-end rows: date -> btc_sold_per_share, proceeds_per_share_usd (12 rows)
- Detects year from the data
- Stores to `data/proceeds/{year}.json`
- Idempotent: re-importing skips if proceeds for that year already exist

---

## Architecture

```
fbtc-taxgrinder/
├── fbtc_taxgrinder/
│   ├── __init__.py
│   ├── db/                    # JSON read/write, data access layer
│   │   ├── __init__.py
│   │   ├── lots.py            # Load/save lots.json
│   │   ├── proceeds.py        # Load/save proceeds/{year}.json
│   │   ├── results.py         # Load/save results/{year}.json
│   │   └── state.py           # Load/save state/{year}.json
│   ├── engine/                # Pure computation, no I/O
│   │   ├── __init__.py
│   │   ├── compute.py         # compute_year() and per-lot-per-month logic
│   │   ├── models.py          # Dataclasses: Lot, LotEvent, MonthResult, YearResult, etc.
│   │   └── matching.py        # Sell-to-lot matching logic
│   ├── parsers/               # External data import
│   │   ├── __init__.py
│   │   ├── etrade.py          # ETrade CSV parser
│   │   └── fidelity_pdf.py    # Fidelity WHFIT PDF parser
│   ├── export/                # Output formatting
│   │   ├── __init__.py
│   │   └── csv_export.py      # CSV export (XLSX, web later)
│   └── cli/                   # Click-based CLI (thin glue)
│       ├── __init__.py
│       └── commands.py
├── data/                      # Persistent JSON storage
│   ├── lots.json
│   ├── proceeds/
│   ├── results/
│   └── state/
├── tests/
│   ├── test_engine.py
│   ├── test_proration.py
│   ├── test_sells.py
│   ├── test_matching.py
│   ├── test_etrade_parser.py
│   └── test_fidelity_parser.py
├── main.py                    # CLI entry point
└── pyproject.toml
```

### Key design decisions

1. **All computations use `Decimal`** for exact arithmetic. FBTC values have 8+ decimal places; float rounding causes drift across 12 months x 15+ lots.

2. **Engine is pure** — receives data, returns results. No file I/O, no database access. This is the layer a future web UI calls directly.

3. **CLI is thin glue** — parses args, calls db/parsers/engine, formats output. Replaceable by a web framework (Flask, FastAPI, etc.) without touching computation logic.

4. **JSON persistence** — human-readable, inspectable, one file per concern. All numeric values stored as strings for Decimal precision.

5. **Lots carry their history** — sell events are attached to the parent lot. Share count at any point is derived from original shares minus cumulative sells.

---

## CLI Interface

```bash
# Import proceeds data (must be done first)
fbtc-taxgrinder import-proceeds --url <fidelity-pdf-url>
fbtc-taxgrinder import-proceeds --file <local.pdf>

# Import trades (buys and sells, requires proceeds for relevant years)
fbtc-taxgrinder import-trades --file <etrade-csv>

# Compute a year (loads prior state automatically)
fbtc-taxgrinder compute --year 2024
fbtc-taxgrinder compute --year 2025          # skips if already computed
fbtc-taxgrinder compute --year 2025 --force  # recompute

# Export results
fbtc-taxgrinder export --year 2024 --format csv --output 2024_report.csv

# Inspect stored data
fbtc-taxgrinder lots      # list all lots and their events
fbtc-taxgrinder status    # show what's imported and computed
```

---

## Export

### CSV Export (initial implementation)

Three output sections:

1. **Per-lot monthly breakdown:** lot_id, month, days_held, days_in_month, total_btc_sold, cost_basis_of_sold, total_expense, gain_loss, adj_btc, adj_basis

2. **Dispositions summary:** lot_id, disposition_id, date_sold, shares_sold, proceeds, disposed_basis, gain_loss

3. **Annual summary:** total_investment_expense, total_reportable_gain, total_cost_basis_of_expense

---

## Testing & Validation

### Test levels

1. **Engine unit tests** — pure function tests with hand-crafted Decimal string inputs
   - Single lot, single month
   - First-month proration (the bug fix)
   - Month with zero expenses (Jan-Jul 2024)
   - Sell event mid-month: split computation, proportional basis reduction
   - Sell matching: unambiguous match, ambiguous match -> error, no match -> error

2. **Cross-reference with existing spreadsheet (2024)**
   - Lots 1-9 (unaffected by proration bug): must match spreadsheet values exactly
   - Lots 10-15 (affected by bug): must differ from spreadsheet in a predictable way; report delta

3. **Chain validation**
   - Compute 2024, then 2025: verify year-end state flows correctly
   - Lot with a 2025 sell: verify adjusted values after disposition

4. **Parser tests**
   - ETrade CSV: filter FBTC rows, handle buys and sells, idempotency
   - Fidelity PDF: extract known values from a test PDF

### Spreadsheet validation data (2024, with bug)

| Lot | Purchase Date | Shares | adj_btc (EOY) | adj_basis (EOY) |
|-----|--------------|--------|---------------|-----------------|
| 1 | 2024-01-25 | 204 | 0.17821032 | 7093.928514 |
| 2 | 2024-02-17 | 2 | 0.00174716 | 91.52566741 |
| 3 | 2024-02-23 | 9 | 0.00786222 | 403.2343991 |
| 4 | 2024-03-06 | 42 | 0.03669036 | 2446.708256 |
| 5 | 2024-03-19 | 1 | 0.00087358 | 56.58068409 |
| 6 | 2024-03-22 | 1 | 0.00087358 | 56.12215668 |
| 7 | 2024-04-18 | 1 | 0.00087358 | 55.76252734 |
| 8 | 2024-04-18 | 54 | 0.04717332 | 2999.831969 |
| 9 | 2024-06-05 | 4 | 0.00349432 | 248.6952777 |
| 10 | 2024-08-19 | 1 | 0.00087347 | 51.34657205 |
| 11 | 2024-08-19 | 5 | 0.00436735 | 256.5700281 |
| 12 | 2024-09-09 | 126 | 0.11006478 | 6231.86185 |
| 13 | 2024-09-09 | 86 | 0.07512358 | 4247.452189 |
| 14 | 2024-10-17 | 82 | 0.07162454 | 4803.869521 |
| 15 | 2024-11-05 | 17 | 0.01485035 | 1041.646881 |

Yearly totals (with bug):
- Total Investment Expense: $39.06
- Total Reportable Gain: $12.83
- Total Cost Basis of Expense: $26.22

### Edge cases

- Lot purchased on the 1st of a month (days_held = full month)
- Lot purchased on the last day of a month (days_held = 0, first active month is next month)
- February in a leap year (days_in_month = 29)
- Month with btc_sold_per_share = 0 (Jan-Jul 2024)
- Multiple sells from the same lot in different months
- Multiple sells from the same lot in the same month
- Sell that fully liquidates a lot (Phase 3 skipped, lot excluded from future months)

---

## Open Questions / Decisions Made

1. **Days-held convention:** `month_end_date - purchase_date` (purchase date not counted). Confirmed by Fidelity example: bought Sep 9, days held = 21 (Sep 30 - Sep 9).

2. **Same-day lots:** Treated as independent lots (e.g., lots 7+8, 10+11, 12+13).

3. **Cost basis method for sells:** Not automatic. Sells are matched to lots by available shares. Ambiguous matches produce an error.

4. **PDF parsing:** Implemented via `pdfplumber`, supporting both URL download and local file.

5. **Persistence:** JSON files, all numerics as strings for Decimal precision.

6. **Idempotent imports:** Re-importing the same data is safe and skips duplicates.

7. **Compute caching:** Results are cached; use `--force` to recompute.

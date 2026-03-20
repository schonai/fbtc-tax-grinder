# Test Coverage Gap Analysis

Analyzed all test files against all source modules on 2026-03-19.

## HIGH PRIORITY — Likely bugs or crash paths

| # | Module | Edge Case | Why it matters |
|---|--------|-----------|----------------|
| 1 | `engine/compute.py:40` | `compute_period` with `days_held=0` | Untested short-circuit branch; could mask bugs |
| 2 | `engine/compute.py:73-74` | `new_adj_btc` going negative (oversized `btc_sold`) | No guard exists — would produce negative BTC, a data integrity issue |
| 3 | `engine/compute.py:229-245` | Full liquidation in PRORATE mode | Entirely distinct code path from FULL_MONTH liquidation; zero tests |
| 4 | `engine/compute.py:391-400` | `prior_state` provided but lot ID missing | Would raise `ValueError` — no test confirms the error message or path |
| 5 | `engine/compute.py:402-405` | Fully liquidated lot (shares=0) from prior state skipped | Skip logic untested; lot should still appear in `end_states` |
| 6 | `parsers/etrade.py:59-62` | Malformed Trade Date, non-numeric Quantity/Price | Causes unhandled `IndexError`/`InvalidOperation` — no try/except, no test |
| 7 | `db/*.py` | Corrupt/invalid JSON in any `load` function | All four loaders crash with `JSONDecodeError`; untested |
| 8 | `db/*.py` | `save` to missing subdirectory | `proceeds.save`, `state.save`, `results.save` would raise `FileNotFoundError` |
| 9 | `db/codec.py:40` | Decimal reconstructed from JSON numeric literal (not string) | `Decimal(0.1)` produces floating-point noise; untested lossy path |
| 10 | `cli/commands.py:125-129` | Buy date exists in proceeds year but specific date missing from `daily` | Only "entire year missing" is tested, not "date missing within year" |

## MEDIUM PRIORITY — Missing branch/path coverage

| # | Module | Edge Case |
|---|--------|-----------|
| 11 | `compute.py:276-277` | Lot purchased after month end — should return `None` |
| 12 | `compute.py:283-285` | PRORATE mode, purchased on last day of month — returns `None` |
| 13 | `compute.py:301` | Out-of-order sell events in `lot.events` — relies on `sorted()` |
| 14 | `compute.py:336-348` | Sell in purchase month with PRORATE mode |
| 15 | `compute.py:443-461` | `compute_year` with empty lots list or multiple lots |
| 16 | `compute.py:196-209` | PRORATE mode sell on first day of month (`pre_days=0`) |
| 17 | `compute.py:134` | Multiple sells fully liquidating then over-selling (hits `shares <= 0` guard) |
| 18 | `matching.py:19` | `purchase_date == sell_date` — lot excluded by `<` filter, boundary untested |
| 19 | `matching.py:31-36` | Multiple exact matches — should trigger ambiguous error |
| 20 | `matching.py:18` | Lots with prior sell events affecting `shares_at_date` candidacy |
| 21 | `cli/commands.py:195-196` | `--full-month --prorate` both specified (mutually exclusive error) |
| 22 | `cli/commands.py:231-232` | `compute_year` raises `ValueError` — `ClickException` |
| 23 | `cli/commands.py:112-115` | Buy idempotency (duplicate buy import) |
| 24 | `cli/commands.py:220-221` | Prior state loading for multi-year CLI compute |
| 25 | `fidelity_pdf.py:83-87` | Multi-page PDF aggregation |
| 26 | `fidelity_pdf.py:90-91` | Duplicate dates across pages — silent overwrite |
| 27 | `etrade.py:63` | Unknown order type (e.g., "Transfer") silently skipped |

## LOW PRIORITY — Unlikely paths or implicit coverage

| # | Module | Edge Case |
|---|--------|-----------|
| 28 | `export/csv_export.py:15` | `mkdir(parents=True)` auto-creates nested output dir |
| 29 | `export/csv_export.py:67-74` | Multi-month summary ordering and rounding |
| 30 | `export/csv_export.py:29-33` | High-precision Decimals unrounded in monthly CSV |
| 31 | `db/codec.py:62` | Missing required field in JSON — silent omission or `TypeError` |
| 32 | `db/codec.py:66` | Fallback `return data` for unknown types |
| 33 | `cli/commands.py:29-30` | `_int_stems` with non-numeric JSON filenames |
| 34 | `cli/commands.py:266-278` | `lots` command with no data / lots with sell events displayed |
| 35 | `cli/commands.py:296-305` | `status` when directories don't exist |
| 36 | `fidelity_pdf.py:130-131` | Network error on URL download |
| 37 | `fidelity_pdf.py:142` | Temp file cleanup on exception |
| 38 | `models.py` | No input validation on dataclass construction (negative shares, empty id) |

## Key Themes

1. **PRORATE mode is under-tested** — Many PRORATE-specific paths (full liquidation, sell on day 1, purchase on last day, sell in purchase month) have zero test coverage while FULL_MONTH equivalents are tested.

2. **Multi-year state chaining** — Prior state loading, missing lots in prior state, and fully liquidated lots from prior years are all untested at both the engine and CLI levels.

3. **Malformed input handling** — ETrade parser has no error handling or tests for bad dates, non-numeric values. The DB layer has no tests for corrupt JSON.

4. **Matching edge cases** — Same-day purchase/sell boundary, lots with prior events, and multiple exact matches are all untested.

5. **DB layer uses only mocks** — No real filesystem roundtrip tests exist for the DB modules. Bugs in actual file I/O (missing directories, encoding) would not be caught.

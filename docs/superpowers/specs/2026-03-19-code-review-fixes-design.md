# Code Review Fixes — Design Spec

Date: 2026-03-19

## Context

An exhaustive code review of the FBTC Tax Grinder codebase identified issues across financial correctness, engine logic, error handling, test coverage, and code quality. This spec covers the 20 fixes that were triaged and approved.

Note: Issue numbers (C1, C2, H6, M12, etc.) correspond to the original code review numbering. Gaps in numbering are items that were triaged to "out of scope" — see the end of this document.

## Fixes

### Critical

#### C1: Off-by-one in prorate sell splitting

**File:** `engine/compute.py` — `_handle_sells_prorate`

**Problem:** The sell date is counted in neither the pre-sell nor post-sell phase, losing one day of trust expense proration per sell event.

**Fix:** On line 215, change:
```python
post_days = Decimal(str((month_end - current_start).days))
```
to:
```python
post_days = Decimal(str((month_end - current_start).days)) + 1
```

This adds the sell date (which is `current_start` after line 212 sets it to `event.date`) to the post-sell phase.

No change to the first-month prorate calculation on line 266 — Fidelity's document confirms 21 days for a 9/9 purchase in a 30-day month, which matches the current exclusive `(month_end - purchase_date).days` formula.

**Edge case:** A sell on the last day of the month (`current_start == month_end`) will produce `post_days = 1`. This is correct — the sell date itself should receive one day of expense proration in the post-sell phase.

#### C2: Division by zero when `adj_btc` is zero

**File:** `engine/compute.py` — `compute_period`

**Problem:** `cost_basis_of_sold = (total_btc_sold / adj_btc) * adj_basis` crashes if `adj_btc == 0`.

**Fix:** Inside the `if monthly_btc_sold_per_share != 0:` block on line 55, add a guard: if `adj_btc == 0`, set both `total_btc_sold = Decimal("0")` and `cost_basis_of_sold = Decimal("0")`, and skip the division. If there is no BTC remaining, there is nothing to sell and no cost basis to allocate. Without this, `total_btc_sold` would be nonzero and Step 6 would subtract it from zero `adj_btc`, producing a negative `new_adj_btc`.

#### C3: Division by zero on `shares` mid-month with multiple sells

**File:** `engine/compute.py` — `_handle_sells_full_month` and `_handle_sells_prorate`

**Problem:** `disposed_btc = adj_btc * (event.shares / shares)` crashes if shares were fully depleted by a prior sell in the same month.

**Fix:** Before each disposition in both `_handle_sells_full_month` (line 130) and `_handle_sells_prorate` (line 200), add:
```python
if shares <= 0 or event.shares > shares:
    raise ValueError(
        f"Sell of {event.shares} shares exceeds remaining {shares} shares for lot {inp.lot.id}"
    )
```
The `shares <= 0` guard catches the case where a prior sell fully depleted the lot. The `event.shares > shares` guard catches oversized sells from data import errors.

#### C4: Prior-year state chain validation — CLI error handling

**File:** `cli/commands.py` — `compute` command

**Problem:** The engine (`compute_year` at line 378) already validates this and raises `ValueError` if a prior-year lot lacks state. However, this `ValueError` propagates as a raw traceback in the CLI.

**Fix:** In the `compute` command, wrap the `compute_year()` call in try/except `ValueError`, and re-raise as `click.ClickException(str(e))`. The engine's error message already contains the lot ID and required year, so just forwarding it is sufficient.

### High

#### H6: Rounding strategy discrepancy — README note

**File:** `README.md`

**Problem:** Full-precision-then-round can differ by 1-2 cents from Fidelity's published example. Neither intermediate rounding nor full precision exactly reproduces Fidelity's -$8.65 example.

**Fix:** Add a note in the README under a new section "Known limitations" explaining the penny-level discrepancy and that the exact internal rounding used by Fidelity cannot be determined from published data.

#### H7: Trust expense only on surviving shares — in-code comment

**File:** `engine/compute.py` — `_handle_sells_full_month`

**Problem:** Design choice is correct but not documented in code.

**Fix:** Add a comment explaining that expense is computed only on surviving shares, matching observed 1099 behavior. No logic change. README already covers this clearly.

#### H8: Duplicate test functions

**File:** `tests/test_sells.py`

**Problem:** `test_sell_expense_only_on_surviving_shares` and `test_full_liquidation_zero_expense` are each defined twice; first copies are dead code.

**Fix:** Verify both copies are identical, then delete the first (earlier) copy of each duplicated function (lines ~230 and ~265). Keep the second copies (lines ~297 and ~332).

#### H9: Add tests for sell processing in `import-trades`

**File:** `tests/test_cli.py`

**Problem:** The sell-processing loop in `import-trades` (matching, idempotency, event creation) has zero test coverage.

**Fix:** Add tests covering:
- Importing a CSV with sell rows, verifying sell events are attached to the correct lot
- Idempotency: re-importing the same sells doesn't duplicate events
- Error case: sell that doesn't match any lot produces a clean error

#### H10: Add tests for multi-year state chaining

**File:** `tests/test_compute.py`

**Problem:** No test passes a non-None `prior_state` to `compute_year`.

**Fix:** Add a test that:
1. Computes year N for a lot, capturing end-of-year state
2. Passes that state as `prior_state` to `compute_year` for year N+1
3. Verifies the lot starts year N+1 with the carried-forward adj_btc, adj_basis, and shares

### Medium

#### M12: ETrade parser column validation

**File:** `parsers/etrade.py`

**Problem:** Raw `KeyError` if CSV column names differ from expected.

**Fix:** At the start of `parse_etrade_rows`, check that all required columns (`Security`, `Trade Date`, `Quantity`, `Executed Price`, `Order Type`, `Net Amount`) exist. Since `rows` is typed as `Iterable[dict]`, use `itertools.chain` to peek at the first row without losing it:
```python
rows_iter = iter(rows)
first = next(rows_iter, None)
if first is None:
    return TradeResult(buys=[], sells=[])
required = {"Security", "Trade Date", "Quantity", "Executed Price", "Order Type", "Net Amount"}
missing = required - first.keys()
if missing:
    raise ValueError(f"Missing required column(s): {', '.join(sorted(missing))}")
for row in itertools.chain([first], rows_iter):
    ...
```
Raise `ValueError` if any required columns are absent.

#### M13: Catch ValueError from match_sell_to_lot

**File:** `cli/commands.py` — `import_trades`

**Problem:** `ValueError` from matching propagates as a traceback.

**Fix:** Wrap the `match_sell_to_lot` call in try/except, re-raise as `click.ClickException` with the same message.

#### M16: Sell idempotency check — also compare price

**File:** `cli/commands.py` — `import_trades`

**Problem:** Two same-day sells of the same share count at different prices are treated as duplicates.

**Fix:** In the idempotency check (currently `e.date == sell["date"] and e.shares == sell["shares"]`), add `e.price_per_share == sell["price_per_share"]`. Both sides: `e` is a `LotEvent` (attribute access), `sell` is a dict from the parser (key access). After M17 is applied, `sell` will be a `SellTrade` dataclass, so adjust to `sell.price_per_share` at that point.

#### M17: Typed parser return structures

**Files:** `parsers/etrade.py`, `parsers/fidelity_pdf.py`

**Problem:** Parsers return plain dicts.

**Fix:** Define dataclasses for parser return values:
- `etrade.py`: A `Trade` dataclass with `date`, `shares`, `price_per_share`, `total_cost` (buys) / `proceeds` (sells) fields. Since buys and sells have different fields, use two dataclasses: `BuyTrade` and `SellTrade`. A `TradeResult` dataclass with `buys: list[BuyTrade]` and `sells: list[SellTrade]` replaces the dict return.
- `fidelity_pdf.py`: `parse_proceeds_line` returns a dict consumed only internally by `parse_proceeds_pdf`, which itself returns `tuple[dict, dict]` (daily_btc, monthly data). Since these are consumed by `commands.py` to build `YearProceeds`, add a `ProceedsRow` dataclass for `parse_proceeds_line` and a `FidelityPdfResult` dataclass for the top-level parse functions (with `daily_btc_per_share: dict[date, Decimal]` and `monthly: dict[date, MonthProceeds]` fields).

Update all consumers to use attribute access instead of dict key access. The only consumer is `cli/commands.py`:
- Buy loop (lines ~101-133): `buy["date"]` → `buy.date`, `buy["shares"]` → `buy.shares`, etc.
- Sell loop (lines ~137-160): `sell["date"]` → `sell.date`, `sell["shares"]` → `sell.shares`, etc.
- Fidelity data (lines ~56-78): adjust to use `FidelityPdfResult` attributes.

**Ordering:** M17, L7, and L8 should be applied in the same step since `fidelity_pdf.py` uses `file_path.split("/")` which would break if `file_path` becomes a `Path` without L8.

#### M18: Remove dead `--format` option

**File:** `cli/commands.py` — `export` command

**Problem:** `--format` accepts only `"csv"` and is never used.

**Fix:** Remove the `--format` option and the `fmt` parameter.

#### M19: CLI tests — assert prerequisite exit codes

**File:** `tests/test_cli.py`

**Problem:** Chained commands don't verify intermediate success.

**Fix:** After each prerequisite `runner.invoke(...)`, assert `result.exit_code == 0` with a descriptive message.

### Low

#### L1: `Decimal(0)` consistency

**File:** `export/csv_export.py`, line 52

**Fix:** Change all three occurrences of `Decimal(0)` to `Decimal("0")` in the `defaultdict` lambda.

#### L3: `sell_events` type annotation

**File:** `engine/compute.py`

**Fix:** Change `sell_events: list` to `sell_events: list[LotEvent]` in `_handle_sells_full_month` and `_handle_sells_prorate`.

#### L7 + L8: Parser path types and `Path.name` (must be applied together)

**Files:** `parsers/etrade.py`, `parsers/fidelity_pdf.py`

**Fix:** Change `file_path: str` to `file_path: str | Path` in parser functions. Use `Path(file_path)` internally where needed. In `fidelity_pdf.py`, replace `file_path.split("/")[-1]` with `Path(file_path).name`. These two fixes are order-dependent: L8 must be applied with L7, otherwise passing a `Path` to `fidelity_pdf.py` would break on `.split("/")`.

#### L10: `status` crashes on non-integer JSON filenames

**File:** `cli/commands.py` — `status` command

**Fix:** Wrap `int(f.stem)` in try/except `ValueError`, skip non-integer filenames.

## Out of scope

The following items were reviewed and explicitly declined:
- Atomic file writes (personal CLI, crash-during-write unlikely)
- JSON deserialization error handling (tracebacks acceptable)
- Monthly CSV rounding (intentionally full precision)
- Explicit Decimal context guard (default 28 digits sufficient)
- `HoldingMode` enum location (leave in compute.py)
- Codec `Optional`/`Union` handling (no current fields use it)
- Codec NaN/Infinity guard (no realistic path to produce these)
- `--full-month` flag being a no-op (documented as default)
- Fragile lot ID generation (unlikely in normal use)
- File descriptor leak on HTTP error (temp file still cleaned up)
- UTF-8 encoding on CSV opens (data is ASCII)

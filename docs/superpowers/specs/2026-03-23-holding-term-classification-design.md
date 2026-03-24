# Holding Term Classification for WHFIT Expense Results

**Date:** 2026-03-23
**Status:** Draft

## Problem

The WHFIT monthly expense gain/loss results currently lack information about whether the underlying tax lot qualifies as long-term or short-term for IRS purposes. This matters for tax reporting: the monthly trust expense gain/loss classification depends on how long the shareholder has held the lot.

## Design

### New Enum: `HoldingTerm`

Add to `models.py`:

```python
class HoldingTerm(Enum):
    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"
```

### Model Change: `ExpenseResult`

Add field `holding_term: HoldingTerm` to `ExpenseResult`.

### IRS Long-Term Rule

A lot is long-term if the sell date is **more than one year** after the purchase date. Using date anniversary (not 365 days):

```python
try:
    anniversary = purchase_date.replace(year=purchase_date.year + 1)
except ValueError:  # Feb 29 leap year edge case
    anniversary = purchase_date.replace(year=purchase_date.year + 1, day=28)
is_long_term = sell_date > anniversary
```

- Purchased 2024-01-15 -> long-term from 2025-01-16 onward
- Purchased 2024-02-29 -> long-term from 2025-03-01 onward

### Computation: `compute_lot_month()`

In `compute_lot_month()`, determine `holding_term` by comparing `month_end` (the sell_date for expense purposes) against `lot.purchase_date + 1 year`. Set this on every `ExpenseResult` produced.

The holding term is a property of the lot-month pair, not of individual periods or sell phases, so it is computed once at the top of `compute_lot_month()` and passed through.

### CSV Export Changes

**Monthly CSV** — add `holding_term` column with the per-lot enum value (`long_term` or `short_term`).

**Summary CSV** — add `holding_term` column. A sell_date row is `long_term` only if every `ExpenseResult` contributing to that row has `holding_term == LONG_TERM`. Otherwise `short_term`. The total row leaves this column blank.

### JSON Serialization (codec.py)

The codec needs to handle `HoldingTerm` enum serialization/deserialization since `ExpenseResult` is part of `YearResult`, which is persisted to JSON.

- `_prepare`: serialize `HoldingTerm` as its `.value` string
- `_reconstruct`: add `Enum` support — detect enum types and reconstruct via `cls(data)`

### Files Changed

| File                          | Change                                                  |
| ----------------------------- | ------------------------------------------------------- |
| `models.py`                   | Add `HoldingTerm` enum, add field to `ExpenseResult`    |
| `engine/compute.py`           | Compute `holding_term`, pass to `ExpenseResult`         |
| `export/csv_export.py`        | Add `holding_term` column to monthly and summary CSVs   |
| `db/codec.py`                 | Add enum serialization/deserialization support           |
| `tests/test_compute.py`       | Test long-term, short-term, Feb 29 edge case            |
| `tests/test_csv_export.py`    | Test holding_term in monthly and summary CSV output      |
| `tests/test_codec.py`         | Test enum round-trip serialization                      |

### Test Cases

1. Lot purchased > 1 year before month-end -> `LONG_TERM`
2. Lot purchased < 1 year before month-end -> `SHORT_TERM`
3. Lot purchased exactly 1 year before month-end -> `SHORT_TERM` (must be *more than* 1 year)
4. Feb 29 purchase date -> long-term from March 1 of following year
5. Summary row with all long-term lots -> `long_term`
6. Summary row with mixed lots -> `short_term`
7. Codec round-trip for `HoldingTerm` enum values

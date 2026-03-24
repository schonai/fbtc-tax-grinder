# Holding Term Classification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `HoldingTerm` enum (`LONG_TERM`/`SHORT_TERM`) to each `ExpenseResult` so WHFIT monthly expense gain/loss can be classified per IRS holding period rules.

**Architecture:** Add enum to `models.py`, compute it in `compute_lot_month()` by comparing `month_end > lot.purchase_date + 1 year`, propagate through CSV export and JSON codec. The holding term is per lot-month; summary CSV aggregates it as `long_term` only when all lots for that date are long-term.

**Tech Stack:** Python stdlib only (no new dependencies).

**Spec:** `docs/superpowers/specs/2026-03-23-holding-term-classification-design.md`

---

## File Structure

| File                                       | Action | Responsibility                                    |
| ------------------------------------------ | ------ | ------------------------------------------------- |
| `fbtc_taxgrinder/models.py`                | Modify | Add `HoldingTerm` enum + field on `ExpenseResult`  |
| `fbtc_taxgrinder/engine/compute.py`        | Modify | Compute and set `holding_term` on `ExpenseResult`  |
| `fbtc_taxgrinder/db/codec.py`              | Modify | Add `Enum` support to `_prepare` and `_reconstruct` |
| `fbtc_taxgrinder/export/csv_export.py`     | Modify | Add `holding_term` column to monthly + summary CSV |
| `tests/test_compute.py`                    | Modify | Add holding term tests, update existing constructions |
| `tests/test_codec.py`                      | Modify | Update `ExpenseResult` constructions, add enum test |
| `tests/test_csv_export.py`                 | Modify | Update `ExpenseResult` constructions, test new column |

---

### Task 1: Add `HoldingTerm` enum and `ExpenseResult` field

**Files:**
- Modify: `fbtc_taxgrinder/models.py:1-83`

- [ ] **Step 1: Add `HoldingTerm` enum and field to `ExpenseResult`**

In `fbtc_taxgrinder/models.py`, add the `Enum` import, the `HoldingTerm` class before `ExpenseResult`, and the `holding_term` field to `ExpenseResult`:

```python
# Add to imports (line 1-7):
from enum import Enum

# Add before the ExpenseResult class (before line 70):
class HoldingTerm(Enum):
    """IRS holding period classification for WHFIT expense gain/loss."""

    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"

# Add field to ExpenseResult (after line 82, the adj_basis field):
    holding_term: HoldingTerm
```

The full `ExpenseResult` should look like:

```python
@dataclass
class ExpenseResult:
    """Result of the 6-step expense calculation for one lot-month."""

    sell_date: date
    days_held: Decimal
    days_in_month: Decimal
    shares: Decimal
    total_btc_sold: Decimal
    cost_basis_of_sold: Decimal
    total_expense: Decimal
    gain_loss: Decimal
    adj_btc: Decimal
    adj_basis: Decimal
    holding_term: HoldingTerm
```

- [ ] **Step 2: Run tests to confirm they fail**

Run: `pytest tests/ -x --tb=short 2>&1 | head -30`
Expected: Multiple failures because existing `ExpenseResult(...)` constructions lack the new `holding_term` field.

- [ ] **Step 3: Commit**

```bash
git add fbtc_taxgrinder/models.py
git commit -m "feat: add HoldingTerm enum and field to ExpenseResult"
```

---

### Task 2: Compute `holding_term` in the engine

**Files:**
- Modify: `fbtc_taxgrinder/engine/compute.py:1-21,308-421`
- Test: `tests/test_compute.py`

- [ ] **Step 1: Write failing tests for holding term computation**

Add these tests to `tests/test_compute.py`. First, add the import:

```python
from fbtc_taxgrinder.models import Lot, LotEvent, LotState, MonthProceeds, YearProceeds, HoldingTerm
```

Then add the test functions:

```python
def test_holding_term_short_term():
    """Lot held < 1 year: purchase 2024-03-15, month-end 2025-01-31 -> SHORT_TERM."""
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 3, 15),
        original_shares=Decimal("100"),
        price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.001"),
        source_file="test.csv",
        events=[],
    )
    mp = MonthProceeds(
        btc_sold_per_share=Decimal("0.00000018"),
        proceeds_per_share_usd=Decimal("0.01070327"),
    )
    result = compute_lot_month(
        LotMonthInput(
            lot=lot, year=2025, month=1,
            adj_btc=Decimal("0.1"), adj_basis=Decimal("5000.00"),
            shares=Decimal("100"), month_proceeds=mp,
        )
    )
    assert result is not None
    assert result.month_result.holding_term == HoldingTerm.SHORT_TERM


def test_holding_term_long_term():
    """Lot held > 1 year: purchase 2024-01-15, month-end 2025-03-31 -> LONG_TERM."""
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 15),
        original_shares=Decimal("100"),
        price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.001"),
        source_file="test.csv",
        events=[],
    )
    mp = MonthProceeds(
        btc_sold_per_share=Decimal("0.00000018"),
        proceeds_per_share_usd=Decimal("0.01070327"),
    )
    result = compute_lot_month(
        LotMonthInput(
            lot=lot, year=2025, month=3,
            adj_btc=Decimal("0.1"), adj_basis=Decimal("5000.00"),
            shares=Decimal("100"), month_proceeds=mp,
        )
    )
    assert result is not None
    assert result.month_result.holding_term == HoldingTerm.LONG_TERM


def test_holding_term_exactly_one_year_is_short_term():
    """Lot held exactly 1 year: purchase 2024-01-31, month-end 2025-01-31 -> SHORT_TERM.
    IRS rule: must be MORE than 1 year."""
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 31),
        original_shares=Decimal("100"),
        price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.001"),
        source_file="test.csv",
        events=[],
    )
    mp = MonthProceeds(
        btc_sold_per_share=Decimal("0.00000018"),
        proceeds_per_share_usd=Decimal("0.01070327"),
    )
    result = compute_lot_month(
        LotMonthInput(
            lot=lot, year=2025, month=1,
            adj_btc=Decimal("0.1"), adj_basis=Decimal("5000.00"),
            shares=Decimal("100"), month_proceeds=mp,
        )
    )
    assert result is not None
    assert result.month_result.holding_term == HoldingTerm.SHORT_TERM


def test_holding_term_feb29_leap_year():
    """Lot purchased Feb 29 (leap year): anniversary is Feb 28 next year,
    so long-term starts March 1."""
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 2, 29),
        original_shares=Decimal("100"),
        price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.001"),
        source_file="test.csv",
        events=[],
    )
    mp = MonthProceeds(
        btc_sold_per_share=Decimal("0.00000018"),
        proceeds_per_share_usd=Decimal("0.01070327"),
    )
    # Feb 2025 (month_end = Feb 28): anniversary is Feb 28, 2/28 > 2/28 is False -> SHORT
    result_feb = compute_lot_month(
        LotMonthInput(
            lot=lot, year=2025, month=2,
            adj_btc=Decimal("0.1"), adj_basis=Decimal("5000.00"),
            shares=Decimal("100"), month_proceeds=mp,
        )
    )
    assert result_feb is not None
    assert result_feb.month_result.holding_term == HoldingTerm.SHORT_TERM

    # March 2025 (month_end = Mar 31): 3/31 > 2/28 is True -> LONG
    result_mar = compute_lot_month(
        LotMonthInput(
            lot=lot, year=2025, month=3,
            adj_btc=Decimal("0.1"), adj_basis=Decimal("5000.00"),
            shares=Decimal("100"), month_proceeds=mp,
        )
    )
    assert result_mar is not None
    assert result_mar.month_result.holding_term == HoldingTerm.LONG_TERM


def test_holding_term_transitions_mid_year():
    """Lot purchased 2024-06-15: short-term through June 2025, long-term from July 2025."""
    lot = Lot(
        id="lot-1",
        purchase_date=date(2024, 6, 15),
        original_shares=Decimal("100"),
        price_per_share=Decimal("50.00"),
        total_cost=Decimal("5000.00"),
        btc_per_share_on_purchase=Decimal("0.001"),
        source_file="test.csv",
        events=[],
    )
    proceeds = YearProceeds(
        daily={},
        monthly={
            date(2025, 6, 30): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01"),
            ),
            date(2025, 7, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01"),
            ),
        },
        source="test",
    )
    result = compute_year(
        lots=[lot],
        proceeds=proceeds,
        prior_state={
            "lot-1": LotState(
                adj_btc=Decimal("0.1"), adj_basis=Decimal("5000.00"),
                shares=Decimal("100"),
            ),
        },
        year=2025,
    )
    june_results = [
        r for r in result.lot_results["lot-1"] if r.sell_date == date(2025, 6, 30)
    ]
    july_results = [
        r for r in result.lot_results["lot-1"] if r.sell_date == date(2025, 7, 31)
    ]
    assert len(june_results) == 1
    assert june_results[0].holding_term == HoldingTerm.SHORT_TERM
    assert len(july_results) == 1
    assert july_results[0].holding_term == HoldingTerm.LONG_TERM
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_compute.py::test_holding_term_short_term -v 2>&1 | tail -5`
Expected: FAIL — `ExpenseResult` missing `holding_term` argument.

- [ ] **Step 3: Implement holding term computation in `compute_lot_month()`**

In `fbtc_taxgrinder/engine/compute.py`:

Add `HoldingTerm` to the existing `from fbtc_taxgrinder.models import (...)` block (note: `from enum import Enum` is already imported in this file for `HoldingMode`):
```python
from fbtc_taxgrinder.models import (
    Disposition,
    HoldingTerm,
    Lot,
    LotEvent,
    LotState,
    MonthProceeds,
    ExpenseResult,
    YearProceeds,
    YearResult,
)
```

Add a helper function after the `_month_start` function (after line 305):

```python
def _holding_term(purchase_date: date, sell_date: date) -> HoldingTerm:
    """Classify as LONG_TERM if held more than one year per IRS rules."""
    try:
        anniversary = purchase_date.replace(year=purchase_date.year + 1)
    except ValueError:
        # Feb 29 -> Feb 28; long-term starts March 1
        anniversary = purchase_date.replace(year=purchase_date.year + 1, day=28)
    if sell_date > anniversary:
        return HoldingTerm.LONG_TERM
    return HoldingTerm.SHORT_TERM
```

In `compute_lot_month()`, compute the holding term early (after the `if inp.lot.purchase_date > month_end: return None` check, around line 323):

```python
    holding_term = _holding_term(inp.lot.purchase_date, month_end)
```

Then add `holding_term=holding_term` to both `ExpenseResult(...)` constructions in `compute_lot_month()`:

1. The no-sells path (around line 364):
```python
            month_result=ExpenseResult(
                sell_date=month_end,
                days_held=full_days_held,
                days_in_month=days_in_month,
                shares=shares,
                total_btc_sold=pr.total_btc_sold,
                cost_basis_of_sold=pr.cost_basis_of_sold,
                total_expense=pr.total_expense,
                gain_loss=pr.gain_loss,
                adj_btc=pr.adj_btc,
                adj_basis=pr.adj_basis,
                holding_term=holding_term,
            ),
```

2. The sells path (around line 405):
```python
            month_result=ExpenseResult(
                sell_date=month_end,
                days_held=full_days_held,
                days_in_month=days_in_month,
                shares=inp.shares,
                total_btc_sold=result.total_btc_sold,
                cost_basis_of_sold=result.total_cost_basis,
                total_expense=result.total_expense,
                gain_loss=result.total_gain_loss,
                adj_btc=result.adj_btc,
                adj_basis=result.adj_basis,
                holding_term=holding_term,
            ),
```

- [ ] **Step 4: Run the new holding term tests**

Run: `pytest tests/test_compute.py -k holding_term -v`
Expected: All 5 new tests PASS.

- [ ] **Step 5: Commit**

```bash
git add fbtc_taxgrinder/engine/compute.py tests/test_compute.py
git commit -m "feat: compute holding_term in compute_lot_month"
```

---

### Task 3: Fix existing tests broken by the new field

**Files:**
- Modify: `tests/test_codec.py:85-136`
- Modify: `tests/test_csv_export.py:11-170`

All existing `ExpenseResult(...)` constructions need `holding_term=HoldingTerm.LONG_TERM` (or `.SHORT_TERM` — the value doesn't matter for these tests; use `LONG_TERM` as a default).

- [ ] **Step 1: Update `tests/test_codec.py`**

Add import:
```python
from fbtc_taxgrinder.models import (
    Disposition,
    HoldingTerm,
    Lot,
    LotEvent,
    LotState,
    MonthProceeds,
    ExpenseResult,
    YearProceeds,
    YearResult,
)
```

In `test_year_result_roundtrip` (line 91), add `holding_term=HoldingTerm.LONG_TERM` to the `ExpenseResult(...)`:
```python
                ExpenseResult(
                    sell_date=date(2024, 8, 31),
                    days_held=Decimal("31"),
                    days_in_month=Decimal("31"),
                    shares=Decimal("204"),
                    total_btc_sold=Decimal("0.00003672"),
                    cost_basis_of_sold=Decimal("1.461695179"),
                    total_expense=Decimal("2.18346708"),
                    gain_loss=Decimal("0.7217719012"),
                    adj_btc=Decimal("0.17835720"),
                    adj_basis=Decimal("7099.778305"),
                    holding_term=HoldingTerm.LONG_TERM,
                ),
```

Also add this assertion to verify enum round-trips (after line 131):
```python
    assert loaded.lot_results["lot-1"][0].holding_term == HoldingTerm.LONG_TERM
```

- [ ] **Step 2: Update `tests/test_csv_export.py`**

Add import:
```python
from fbtc_taxgrinder.models import Disposition, ExpenseResult, HoldingTerm, YearResult
```

Add `holding_term=HoldingTerm.LONG_TERM` to every `ExpenseResult(...)` in this file. There are 3 instances:

1. `test_export_creates_three_files` (line 17): add `holding_term=HoldingTerm.LONG_TERM`
2. `test_summary_aggregates_across_lots` — the `er_kwargs` dict (line 89): add `"holding_term": HoldingTerm.LONG_TERM`
3. `test_summary_rounds_to_cents` — the `er_kwargs` dict (line 135): add `"holding_term": HoldingTerm.LONG_TERM`

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ -v`
Expected: All tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/test_codec.py tests/test_csv_export.py
git commit -m "test: update existing tests for new holding_term field"
```

---

### Task 4: Add enum support to JSON codec

**Files:**
- Modify: `fbtc_taxgrinder/db/codec.py:37-71`
- Test: `tests/test_codec.py`

- [ ] **Step 1: Write a failing test for enum round-trip**

Add to `tests/test_codec.py`:

```python
def test_holding_term_enum_roundtrip():
    """HoldingTerm enum survives encode/decode via ExpenseResult in YearResult."""
    yr = YearResult(
        year=2025,
        lot_results={
            "lot-1": [
                ExpenseResult(
                    sell_date=date(2025, 3, 31),
                    days_held=Decimal("31"),
                    days_in_month=Decimal("31"),
                    shares=Decimal("100"),
                    total_btc_sold=Decimal("0.00001"),
                    cost_basis_of_sold=Decimal("0.50"),
                    total_expense=Decimal("1.00"),
                    gain_loss=Decimal("0.50"),
                    adj_btc=Decimal("0.099"),
                    adj_basis=Decimal("4999.50"),
                    holding_term=HoldingTerm.SHORT_TERM,
                ),
            ],
        },
        dispositions=[],
        end_states={},
        total_investment_expense=Decimal("1.00"),
        total_reportable_gain=Decimal("0.50"),
        total_cost_basis_of_expense=Decimal("0.50"),
    )
    text = encode(yr)
    loaded = decode(YearResult, text)
    assert loaded.lot_results["lot-1"][0].holding_term == HoldingTerm.SHORT_TERM
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_codec.py::test_holding_term_enum_roundtrip -v`
Expected: FAIL — `encode()` raises `TypeError: Object of type HoldingTerm is not JSON serializable` (or `_reconstruct` returns raw string if `_prepare` is fixed first).

- [ ] **Step 3: Add enum support to `_prepare` and `_reconstruct` in `codec.py`**

In `fbtc_taxgrinder/db/codec.py`:

Add import:
```python
from enum import Enum
```

In `_prepare`, add an Enum check before the `return obj` fallback (before line 34). `dataclasses.asdict()` does NOT convert Enum values — it deep-copies them, leaving Enum instances that `json.dumps` can't serialize:

```python
    if isinstance(obj, Enum):
        return obj.value
    return obj
```

In `_reconstruct`, add an enum check after the `if cls is int:` block (after line 48):

```python
    if isinstance(cls, type) and issubclass(cls, Enum):
        return cls(data)
```

The full `_prepare` tail should read:
```python
    if isinstance(obj, list):
        return [_prepare(v) for v in obj]
    if isinstance(obj, Enum):
        return obj.value
    return obj
```

The full `_reconstruct` early-return section should read:
```python
    if cls is str:
        return data
    if cls is int:
        return data
    if isinstance(cls, type) and issubclass(cls, Enum):
        return cls(data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_codec.py -v`
Expected: All tests PASS (including the new `test_holding_term_enum_roundtrip`).

- [ ] **Step 5: Commit**

```bash
git add fbtc_taxgrinder/db/codec.py tests/test_codec.py
git commit -m "feat: add Enum support to JSON codec"
```

---

### Task 5: Add `holding_term` to CSV exports

**Files:**
- Modify: `fbtc_taxgrinder/export/csv_export.py:1-131`
- Test: `tests/test_csv_export.py`

- [ ] **Step 1: Write failing tests for CSV holding_term columns**

Add to `tests/test_csv_export.py`:

```python
def test_monthly_csv_includes_holding_term(tmp_path):
    """Monthly CSV rows include the holding_term column."""
    yr = YearResult(
        year=2025,
        lot_results={
            "lot-1": [
                ExpenseResult(
                    sell_date=date(2025, 3, 31),
                    days_held=Decimal("31"),
                    days_in_month=Decimal("31"),
                    shares=Decimal("100"),
                    total_btc_sold=Decimal("0.00001"),
                    cost_basis_of_sold=Decimal("0.50"),
                    total_expense=Decimal("1.00"),
                    gain_loss=Decimal("0.50"),
                    adj_btc=Decimal("0.099"),
                    adj_basis=Decimal("4999.50"),
                    holding_term=HoldingTerm.LONG_TERM,
                ),
            ],
        },
        dispositions=[],
        end_states={},
        total_investment_expense=Decimal("1.00"),
        total_reportable_gain=Decimal("0.50"),
        total_cost_basis_of_expense=Decimal("0.50"),
    )
    export_year_csv(yr, tmp_path)
    with open(tmp_path / "2025_monthly.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["holding_term"] == "long_term"


def test_summary_csv_holding_term_all_long(tmp_path):
    """Summary row is long_term when all lots for that date are long_term."""
    yr = YearResult(
        year=2025,
        lot_results={
            "lot-1": [
                ExpenseResult(
                    sell_date=date(2025, 3, 31),
                    days_held=Decimal("31"), days_in_month=Decimal("31"),
                    shares=Decimal("100"), total_btc_sold=Decimal("0.00001"),
                    cost_basis_of_sold=Decimal("0.50"), total_expense=Decimal("1.00"),
                    gain_loss=Decimal("0.50"), adj_btc=Decimal("0.099"),
                    adj_basis=Decimal("4999.50"),
                    holding_term=HoldingTerm.LONG_TERM,
                ),
            ],
            "lot-2": [
                ExpenseResult(
                    sell_date=date(2025, 3, 31),
                    days_held=Decimal("31"), days_in_month=Decimal("31"),
                    shares=Decimal("50"), total_btc_sold=Decimal("0.00001"),
                    cost_basis_of_sold=Decimal("0.25"), total_expense=Decimal("0.50"),
                    gain_loss=Decimal("0.25"), adj_btc=Decimal("0.049"),
                    adj_basis=Decimal("2499.75"),
                    holding_term=HoldingTerm.LONG_TERM,
                ),
            ],
        },
        dispositions=[],
        end_states={},
        total_investment_expense=Decimal("1.50"),
        total_reportable_gain=Decimal("0.75"),
        total_cost_basis_of_expense=Decimal("0.75"),
    )
    export_year_csv(yr, tmp_path)
    with open(tmp_path / "2025_summary.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["holding_term"] == "long_term"
    assert rows[1]["holding_term"] == ""  # total row is blank


def test_summary_csv_holding_term_mixed(tmp_path):
    """Summary row is short_term when any lot for that date is short_term."""
    yr = YearResult(
        year=2025,
        lot_results={
            "lot-1": [
                ExpenseResult(
                    sell_date=date(2025, 3, 31),
                    days_held=Decimal("31"), days_in_month=Decimal("31"),
                    shares=Decimal("100"), total_btc_sold=Decimal("0.00001"),
                    cost_basis_of_sold=Decimal("0.50"), total_expense=Decimal("1.00"),
                    gain_loss=Decimal("0.50"), adj_btc=Decimal("0.099"),
                    adj_basis=Decimal("4999.50"),
                    holding_term=HoldingTerm.LONG_TERM,
                ),
            ],
            "lot-2": [
                ExpenseResult(
                    sell_date=date(2025, 3, 31),
                    days_held=Decimal("31"), days_in_month=Decimal("31"),
                    shares=Decimal("50"), total_btc_sold=Decimal("0.00001"),
                    cost_basis_of_sold=Decimal("0.25"), total_expense=Decimal("0.50"),
                    gain_loss=Decimal("0.25"), adj_btc=Decimal("0.049"),
                    adj_basis=Decimal("2499.75"),
                    holding_term=HoldingTerm.SHORT_TERM,
                ),
            ],
        },
        dispositions=[],
        end_states={},
        total_investment_expense=Decimal("1.50"),
        total_reportable_gain=Decimal("0.75"),
        total_cost_basis_of_expense=Decimal("0.75"),
    )
    export_year_csv(yr, tmp_path)
    with open(tmp_path / "2025_summary.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["holding_term"] == "short_term"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_csv_export.py::test_monthly_csv_includes_holding_term -v`
Expected: FAIL — `holding_term` key not in CSV row.

- [ ] **Step 3: Add `holding_term` to CSV export**

In `fbtc_taxgrinder/export/csv_export.py`:

Add import:
```python
from fbtc_taxgrinder.models import HoldingTerm, YearResult
```

**Monthly CSV** — add `"holding_term"` to the header (after `"adj_basis"`), and add `er.holding_term.value` to each data row (after `er.adj_basis`):

```python
        writer.writerow(
            [
                "lot_id",
                "sell_date",
                "days_held",
                "days_in_month",
                "shares",
                "total_btc_sold",
                "cost_basis_of_sold",
                "total_expense",
                "gain_loss",
                "adj_btc",
                "adj_basis",
                "holding_term",
            ]
        )
        for lot_id, results in sorted(year_result.lot_results.items()):
            for er in results:
                writer.writerow(
                    [
                        lot_id,
                        er.sell_date.isoformat(),
                        er.days_held,
                        er.days_in_month,
                        er.shares,
                        er.total_btc_sold,
                        er.cost_basis_of_sold,
                        er.total_expense,
                        er.gain_loss,
                        er.adj_btc,
                        er.adj_basis,
                        er.holding_term.value,
                    ]
                )
```

**Summary CSV** — track holding term per sell_date. Update the `date_agg` defaultdict to include an `"all_long_term"` boolean, then add the column.

Replace the summary section (lines 88-130) with:

```python
    # Summary: per-sell-date aggregates + annual total
    date_agg: dict[date, dict[str, Decimal]] = defaultdict(
        lambda: {
            "investment_expense": Decimal("0"),
            "cost_basis_of_expense": Decimal("0"),
            "reportable_gain": Decimal("0"),
        }
    )
    date_holding: dict[date, bool] = defaultdict(lambda: True)  # all_long_term
    for results in year_result.lot_results.values():
        for er in results:
            date_agg[er.sell_date]["investment_expense"] += er.total_expense
            date_agg[er.sell_date]["cost_basis_of_expense"] += er.cost_basis_of_sold
            date_agg[er.sell_date]["reportable_gain"] += er.gain_loss
            if er.holding_term != HoldingTerm.LONG_TERM:
                date_holding[er.sell_date] = False

    summary_path = output_dir / f"{year}_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "sell_date",
                "investment_expense",
                "cost_basis_of_expense",
                "reportable_gain",
                "holding_term",
            ]
        )
        for sell_date in sorted(date_agg):
            agg = date_agg[sell_date]
            holding = (
                HoldingTerm.LONG_TERM if date_holding[sell_date]
                else HoldingTerm.SHORT_TERM
            )
            writer.writerow(
                [
                    sell_date.isoformat(),
                    agg["investment_expense"].quantize(CENTS, ROUND_HALF_UP),
                    agg["cost_basis_of_expense"].quantize(CENTS, ROUND_HALF_UP),
                    agg["reportable_gain"].quantize(CENTS, ROUND_HALF_UP),
                    holding.value,
                ]
            )
        writer.writerow(
            [
                "total",
                year_result.total_investment_expense.quantize(CENTS, ROUND_HALF_UP),
                year_result.total_cost_basis_of_expense.quantize(CENTS, ROUND_HALF_UP),
                year_result.total_reportable_gain.quantize(CENTS, ROUND_HALF_UP),
                "",
            ]
        )
```

- [ ] **Step 4: Run all CSV export tests**

Run: `pytest tests/test_csv_export.py -v`
Expected: All tests PASS.

- [ ] **Step 5: Commit**

```bash
git add fbtc_taxgrinder/export/csv_export.py tests/test_csv_export.py
git commit -m "feat: add holding_term column to monthly and summary CSVs"
```

---

### Task 6: Final verification

- [ ] **Step 1: Run full test suite with coverage**

Run: `pytest --cov=fbtc_taxgrinder --cov-report=term-missing --cov-fail-under=90`
Expected: All tests PASS, coverage >= 90%.

- [ ] **Step 2: Run linting**

Run: `flake8 fbtc_taxgrinder/ tests/`
Expected: No errors.

- [ ] **Step 3: Commit any remaining fixes if needed**

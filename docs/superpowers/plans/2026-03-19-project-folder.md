# Project Folder Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace `--data-dir` and `--output` CLI options with a single required `--project` option.

**Architecture:** Rename the top-level CLI option and its helper/context key, absorb export output into the project folder, update all tests.

**Tech Stack:** Python, Click, pytest

---

### Task 1: Update CLI commands.py

**Files:**
- Modify: `fbtc_taxgrinder/cli/commands.py`

- [ ] **Step 1: Rename helper function and context key**

In `fbtc_taxgrinder/cli/commands.py`, change:

```python
def _data_dir(ctx: click.Context) -> Path:
    return ctx.obj["data_dir"]
```

to:

```python
def _project_dir(ctx: click.Context) -> Path:
    return ctx.obj["project_dir"]
```

- [ ] **Step 2: Update the `cli` group option**

Change the `cli` function from:

```python
@click.group()
@click.option(
    "--data-dir",
    type=click.Path(path_type=Path),
    default=Path("data"),
    help="Path to data directory.",
)
@click.pass_context
def cli(ctx: click.Context, data_dir: Path) -> None:
    """FBTC Tax Lot Grinder — compute IRS-reportable WHFIT tax lots."""
    ctx.ensure_object(dict)
    ctx.obj["data_dir"] = data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "proceeds").mkdir(exist_ok=True)
    (data_dir / "results").mkdir(exist_ok=True)
    (data_dir / "state").mkdir(exist_ok=True)
```

to:

```python
@click.group()
@click.option(
    "--project",
    "project_dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Path to project directory.",
)
@click.pass_context
def cli(ctx: click.Context, project_dir: Path) -> None:
    """FBTC Tax Lot Grinder — compute IRS-reportable WHFIT tax lots."""
    ctx.ensure_object(dict)
    ctx.obj["project_dir"] = project_dir
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "proceeds").mkdir(exist_ok=True)
    (project_dir / "results").mkdir(exist_ok=True)
    (project_dir / "state").mkdir(exist_ok=True)
    (project_dir / "output").mkdir(exist_ok=True)
```

- [ ] **Step 3: Update all `_data_dir` calls to `_project_dir`**

Replace every `_data_dir(ctx)` call in the file with `_project_dir(ctx)`. There are 6 occurrences: in `import_proceeds`, `import_trades`, `compute`, `export`, `list_lots`, and `status`.

Also replace `dd = _data_dir(ctx)` with `dd = _project_dir(ctx)` — the local variable name `dd` stays the same.

- [ ] **Step 4: Update the `export` command**

Change the `export` command from:

```python
@cli.command()
@click.option("--year", required=True, type=int)
@click.option("--output", "output_dir", required=True, type=click.Path(path_type=Path))
@click.pass_context
def export(ctx: click.Context, year: int, output_dir: Path) -> None:
    """Export computed results."""
    dd = _data_dir(ctx)
    yr = results_db.load(dd, year)
    if yr is None:
        raise click.ClickException(f"No results for {year}. Run 'compute' first.")
    export_year_csv(yr, output_dir)
    click.echo(f"Exported {year} results to {output_dir}/")
```

to:

```python
@cli.command()
@click.option("--year", required=True, type=int)
@click.pass_context
def export(ctx: click.Context, year: int) -> None:
    """Export computed results."""
    dd = _project_dir(ctx)
    yr = results_db.load(dd, year)
    if yr is None:
        raise click.ClickException(f"No results for {year}. Run 'compute' first.")
    output_dir = dd / "output"
    export_year_csv(yr, output_dir)
    click.echo(f"Exported {year} results to {output_dir}/")
```

- [ ] **Step 5: Run tests (expect failures from old test references)**

Run: `pytest tests/test_cli.py -x -v 2>&1 | head -30`
Expected: Failures because tests still pass `--data-dir`

- [ ] **Step 6: Commit**

```bash
git add fbtc_taxgrinder/cli/commands.py
git commit -m "refactor: replace --data-dir and --output with --project"
```

---

### Task 2: Update test fixtures and test_cli.py

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_cli.py`

- [ ] **Step 1: Update conftest.py fixture**

Change `tests/conftest.py` from:

```python
@pytest.fixture
def data_dir(tmp_path):
    """Create a temporary data directory with subdirs."""
    (tmp_path / "proceeds").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "state").mkdir()
    return tmp_path
```

to:

```python
@pytest.fixture
def project_dir(tmp_path):
    """Create a temporary project directory with subdirs."""
    (tmp_path / "proceeds").mkdir()
    (tmp_path / "results").mkdir()
    (tmp_path / "state").mkdir()
    (tmp_path / "output").mkdir()
    return tmp_path
```

- [ ] **Step 2: Update test_cli.py — rename fixture parameter and CLI flag**

In `tests/test_cli.py`, make these bulk replacements:

1. Replace all `(data_dir)` and `(data_dir,` fixture parameters with `(project_dir)` and `(project_dir,`
2. Replace all `"--data-dir", str(data_dir)` with `"--project", str(project_dir)`
3. Replace all `str(data_dir)` (non-CLI uses like `_save_test_proceeds(data_dir)`) with `str(project_dir)` — but keep the function parameter names in `_save_test_proceeds` and `_write_etrade_csv` as-is since those are local helpers taking a `data_dir: Path` argument
4. Replace all bare `data_dir` references (like `_save_test_proceeds(data_dir)`, `lots_db.load(data_dir)`) with `project_dir`

The helper functions `_save_test_proceeds` and `_write_etrade_csv` keep their internal parameter name `data_dir` since they pass it to DB functions which also use `data_dir`.

- [ ] **Step 3: Update export tests — remove --output flag**

In `test_export_missing_results`: change from:
```python
result = runner.invoke(cli, [
    "--data-dir", str(data_dir),
    "export", "--year", "2024", "--output", str(data_dir / "out"),
])
```
to:
```python
result = runner.invoke(cli, [
    "--project", str(project_dir),
    "export", "--year", "2024",
])
```

In `test_export_happy_path`: change from:
```python
out_dir = tmp_path / "export"
result = runner.invoke(cli, [
    "--data-dir", str(data_dir),
    "export", "--year", "2024", "--output", str(out_dir),
])
assert result.exit_code == 0
assert "Exported" in result.output
assert (out_dir / "2024_monthly.csv").exists()
```
to:
```python
result = runner.invoke(cli, [
    "--project", str(project_dir),
    "export", "--year", "2024",
])
assert result.exit_code == 0
assert "Exported" in result.output
assert (project_dir / "output" / "2024_monthly.csv").exists()
```

In `test_e2e_workflow`: change the export section from:
```python
output_dir = tmp_path / "output"
result = runner.invoke(cli, [
    "--data-dir", str(data_dir),
    "export", "--year", "2024",
    "--output", str(output_dir),
])
assert result.exit_code == 0, result.output
assert (output_dir / "2024_monthly.csv").exists()
assert (output_dir / "2024_summary.csv").exists()
```
to:
```python
result = runner.invoke(cli, [
    "--project", str(project_dir),
    "export", "--year", "2024",
])
assert result.exit_code == 0, result.output
assert (project_dir / "output" / "2024_monthly.csv").exists()
assert (project_dir / "output" / "2024_summary.csv").exists()
```

- [ ] **Step 4: Run all tests**

Run: `pytest --cov=fbtc_taxgrinder --cov-report=term-missing --cov-fail-under=90 -v`
Expected: All pass, coverage >= 90%

- [ ] **Step 5: Commit**

```bash
git add tests/conftest.py tests/test_cli.py
git commit -m "test: update tests for --project flag rename"
```

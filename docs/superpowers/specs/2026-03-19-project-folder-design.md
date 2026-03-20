# Project Folder Design

## Summary

Replace the `--data-dir` CLI option and separate `--output` export flag with a single required `--project` option that points to a unified project/working folder. All data and output live under this one directory.

## Motivation

Currently, the CLI requires specifying `--data-dir` for data storage and a separate `--output` path for CSV export. This means tracking two locations per project instance. A single `--project` folder simplifies usage and makes it easy to refer to one place for all state related to a particular tax computation.

## Design

### CLI Changes

**Top-level group (`cli`):**
- Rename `--data-dir` option to `--project`
- Make `--project` required (no default value)
- Rename context key from `data_dir` to `project_dir`
- Rename helper `_data_dir()` to `_project_dir()`
- Auto-create project folder and subdirs: `proceeds/`, `results/`, `state/`, `output/`

**`export` command:**
- Remove `--output` / `output_dir` parameter
- Output always writes to `<project>/output/`

**All other commands:**
- Replace `_data_dir(ctx)` calls with `_project_dir(ctx)` — no behavior change

### Project Folder Structure

```
<project>/
  lots.json
  proceeds/
    2025.json
  results/
    2025.json
  state/
    2025.json
  output/
    2025_monthly.csv
    2025_dispositions.csv
    2025_summary.csv
```

This is the existing `data/` layout with `output/` added as a sibling directory.

### Usage

```bash
fbtc-taxgrinder --project ./my-2025 import-proceeds --file fbtc-2025.pdf
fbtc-taxgrinder --project ./my-2025 import-trades --file trades.csv
fbtc-taxgrinder --project ./my-2025 compute --year 2025
fbtc-taxgrinder --project ./my-2025 export --year 2025
```

### Files Changed

1. **`fbtc_taxgrinder/cli/commands.py`** — Rename option, helper, context key; remove `--output` from export; add `output/` to auto-created subdirs; hardcode export output path
2. **`tests/`** — Update all references to `--data-dir` / `data_dir` to `--project` / `project_dir`; update export tests that pass `--output`
3. **`CLAUDE.md`** — Update architecture description if it references `--data-dir` or `--output`

### What Does NOT Change

- Internal data format (JSON files, codec)
- Computation engine
- CSV export logic (only the output path changes)
- Parser modules
- Models

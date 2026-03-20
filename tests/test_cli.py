import csv
from datetime import date
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from fbtc_taxgrinder.cli.commands import cli
from fbtc_taxgrinder.db import lots as lots_db
from fbtc_taxgrinder.db import proceeds as proceeds_db
from fbtc_taxgrinder.models import MonthProceeds, YearProceeds


def _save_test_proceeds(data_dir: Path) -> None:
    """Save minimal 2024 proceeds for testing."""
    yp = YearProceeds(
        daily={date(2024, 1, 25): Decimal("0.00087448")},
        monthly={
            date(2024, 8, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000018"),
                proceeds_per_share_usd=Decimal("0.01070327"),
            ),
        },
        source="test.pdf",
    )
    proceeds_db.save(data_dir, 2024, yp)


def _write_etrade_csv(path: Path) -> None:
    """Write a minimal ETrade CSV for testing."""
    fieldnames = [
        "Trade Date",
        "Order Type",
        "Security",
        "Cusip",
        "Transaction Description",
        "Quantity",
        "Executed Price",
        "Commission",
        "Net Amount",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "Trade Date": "1/25/2024",
                "Order Type": "Buy",
                "Security": "FBTC",
                "Cusip": "315948109",
                "Transaction Description": "FBTC",
                "Quantity": "204",
                "Executed Price": "34.81",
                "Commission": "0.00",
                "Net Amount": "7101.24",
            }
        )


def _write_etrade_csv_with_sell(path: Path) -> None:
    """Write an ETrade CSV with both a buy and a sell row."""
    fieldnames = [
        "Trade Date",
        "Order Type",
        "Security",
        "Cusip",
        "Transaction Description",
        "Quantity",
        "Executed Price",
        "Commission",
        "Net Amount",
    ]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "Trade Date": "1/25/2024",
                "Order Type": "Buy",
                "Security": "FBTC",
                "Cusip": "315948109",
                "Transaction Description": "FBTC",
                "Quantity": "204",
                "Executed Price": "34.81",
                "Commission": "0.00",
                "Net Amount": "7101.24",
            }
        )
        writer.writerow(
            {
                "Trade Date": "8/15/2024",
                "Order Type": "Sell",
                "Security": "FBTC",
                "Cusip": "315948109",
                "Transaction Description": "FBTC",
                "Quantity": "100",
                "Executed Price": "50.00",
                "Commission": "0.00",
                "Net Amount": "5000.00",
            }
        )


# --- Error path tests ---


def test_import_proceeds_missing_file(project_dir):
    """import-proceeds --file with nonexistent file should error."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-proceeds",
            "--file",
            "/nonexistent.pdf",
        ],
    )
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "error" in result.output.lower()


def test_import_proceeds_no_source(project_dir):
    """import-proceeds without --url or --file should error."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-proceeds",
        ],
    )
    assert result.exit_code != 0


def test_compute_missing_proceeds(project_dir):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "compute",
            "--year",
            "2024",
        ],
    )
    assert result.exit_code != 0


def test_export_missing_results(project_dir):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "export",
            "--year",
            "2024",
        ],
    )
    assert result.exit_code != 0
    assert "No results" in result.output


# --- Happy path tests ---


def test_import_proceeds_from_file(project_dir):
    """import-proceeds --file with a mocked PDF parser."""
    mock_yp = YearProceeds(
        daily={date(2024, 1, 11): Decimal("0.00087448")},
        monthly={},
        source="test.pdf",
    )
    with patch(
        "fbtc_taxgrinder.cli.commands.parse_fidelity_pdf_file", return_value=mock_yp
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project",
                str(project_dir),
                "import-proceeds",
                "--file",
                __file__,  # use any existing file
            ],
        )
    assert result.exit_code == 0
    assert "Imported 2024" in result.output


def test_import_proceeds_from_url(project_dir):
    """import-proceeds --url with a mocked PDF parser."""
    mock_yp = YearProceeds(
        daily={date(2024, 1, 11): Decimal("0.00087448")},
        monthly={},
        source="test.pdf",
    )
    with patch(
        "fbtc_taxgrinder.cli.commands.parse_fidelity_pdf_url", return_value=mock_yp
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project",
                str(project_dir),
                "import-proceeds",
                "--url",
                "https://example.com/test.pdf",
            ],
        )
    assert result.exit_code == 0
    assert "Imported 2024" in result.output


def test_import_proceeds_idempotent(project_dir):
    """Second import of same year should skip."""
    _save_test_proceeds(project_dir)
    mock_yp = YearProceeds(
        daily={date(2024, 1, 25): Decimal("0.00087448")},
        monthly={},
        source="test2.pdf",
    )
    with patch(
        "fbtc_taxgrinder.cli.commands.parse_fidelity_pdf_file", return_value=mock_yp
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project",
                str(project_dir),
                "import-proceeds",
                "--file",
                __file__,
            ],
        )
    assert result.exit_code == 0
    assert "already imported" in result.output


def test_import_proceeds_empty_pdf(project_dir):
    """PDF with no data should error."""
    mock_yp = YearProceeds(daily={}, monthly={}, source="empty.pdf")
    with patch(
        "fbtc_taxgrinder.cli.commands.parse_fidelity_pdf_file", return_value=mock_yp
    ):
        runner = CliRunner()
        result = runner.invoke(
            cli,
            [
                "--project",
                str(project_dir),
                "import-proceeds",
                "--file",
                __file__,
            ],
        )
    assert result.exit_code != 0
    assert "No data" in result.output


def test_import_trades(project_dir, tmp_path):
    """Full import-trades happy path."""
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code == 0
    assert "1 new lots" in result.output


def test_import_trades_missing_file(project_dir):
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            "/nonexistent.csv",
        ],
    )
    assert result.exit_code != 0


def test_import_trades_missing_proceeds(project_dir, tmp_path):
    """import-trades without proceeds should error."""
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code != 0
    assert "not imported" in result.output.lower() or "import-proceeds" in result.output


def test_import_trades_with_sells(project_dir, tmp_path):
    """Import trades with a sell row creates lot and sell event."""
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv_with_sell(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "1 new lots" in result.output
    assert "1 new sells" in result.output

    # Verify sell event on the lot
    lots = lots_db.load(project_dir)
    assert len(lots) == 1
    lot = lots[0]
    sell_events = [e for e in lot.events if e.type == "sell"]
    assert len(sell_events) == 1
    assert sell_events[0].date == date(2024, 8, 15)
    assert sell_events[0].shares == Decimal("100")
    assert sell_events[0].price_per_share == Decimal("50.00")


def test_import_trades_sell_idempotent(project_dir, tmp_path):
    """Importing the same sells twice should produce 0 new sells on second run."""
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv_with_sell(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code == 0, result.output

    # Second import
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "0 new sells" in result.output


def test_import_trades_sell_no_match(project_dir, tmp_path):
    """Sell with no matching lot should fail."""
    _save_test_proceeds(project_dir)
    # Write CSV with only a sell (no buy) — no lot will match
    fieldnames = [
        "Trade Date",
        "Order Type",
        "Security",
        "Cusip",
        "Transaction Description",
        "Quantity",
        "Executed Price",
        "Commission",
        "Net Amount",
    ]
    csv_path = tmp_path / "trades.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow(
            {
                "Trade Date": "8/15/2024",
                "Order Type": "Sell",
                "Security": "FBTC",
                "Cusip": "315948109",
                "Transaction Description": "FBTC",
                "Quantity": "100",
                "Executed Price": "50.00",
                "Commission": "0.00",
                "Net Amount": "5000.00",
            }
        )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code != 0


def test_compute_happy_path(project_dir, tmp_path):
    """Full compute happy path."""
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    # Import trades first
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code == 0, result.output
    # Compute
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "compute",
            "--year",
            "2024",
        ],
    )
    assert result.exit_code == 0
    assert "Computed 2024" in result.output


def test_compute_already_exists(project_dir, tmp_path):
    """Compute without --force when results exist should skip."""
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "compute",
            "--year",
            "2024",
        ],
    )
    assert result.exit_code == 0, result.output
    # Second compute should skip
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "compute",
            "--year",
            "2024",
        ],
    )
    assert result.exit_code == 0
    assert "already computed" in result.output


def test_compute_no_lots(project_dir):
    """Compute without lots should error."""
    _save_test_proceeds(project_dir)
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "compute",
            "--year",
            "2024",
        ],
    )
    assert result.exit_code != 0
    assert "No lots" in result.output


def test_export_happy_path(project_dir):
    """Full export happy path."""
    _save_test_proceeds(project_dir)
    csv_path = project_dir / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project", str(project_dir), "import-trades", "--file", str(csv_path)]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        cli, ["--project", str(project_dir), "compute", "--year", "2024"]
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "export",
            "--year",
            "2024",
        ],
    )
    assert result.exit_code == 0
    assert "Exported" in result.output
    assert (project_dir / "output" / "2024_monthly.csv").exists()


def test_lots_with_data(project_dir, tmp_path):
    """lots command with imported data."""
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project", str(project_dir), "import-trades", "--file", str(csv_path)]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli, ["--project", str(project_dir), "lots"])
    assert result.exit_code == 0
    assert "lot-1" in result.output
    assert "204" in result.output


def test_status_empty(project_dir):
    runner = CliRunner()
    result = runner.invoke(cli, ["--project", str(project_dir), "status"])
    assert result.exit_code == 0
    assert "0 lots" in result.output


def test_status_with_data(project_dir, tmp_path):
    """status command with imported data."""
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project", str(project_dir), "import-trades", "--file", str(csv_path)]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        cli, ["--project", str(project_dir), "compute", "--year", "2024"]
    )
    assert result.exit_code == 0, result.output

    result = runner.invoke(cli, ["--project", str(project_dir), "status"])
    assert result.exit_code == 0
    assert "1 lots" in result.output
    assert "2024" in result.output


def test_import_trades_date_missing_in_proceeds(project_dir, tmp_path):
    """Buy date exists in proceeds year but specific date missing from daily data."""
    yp = YearProceeds(
        daily={date(2024, 2, 1): Decimal("0.00087448")},  # different date than buy
        monthly={},
        source="test.pdf",
    )
    proceeds_db.save(project_dir, 2024, yp)

    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)  # buy date is 1/25/2024

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code != 0
    assert "No BTC-per-share data" in result.output


def test_compute_mutually_exclusive_flags(project_dir):
    """--full-month and --prorate together should error."""
    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "compute",
            "--year",
            "2024",
            "--full-month",
            "--prorate",
        ],
    )
    assert result.exit_code != 0
    assert "mutually exclusive" in result.output.lower()


def test_compute_loads_prior_state(project_dir, tmp_path):
    """Multi-year compute: 2025 should load 2024 state."""
    # Set up 2024 data and compute
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project", str(project_dir), "import-trades", "--file", str(csv_path)]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(
        cli, ["--project", str(project_dir), "compute", "--year", "2024"]
    )
    assert result.exit_code == 0, result.output

    # Set up 2025 proceeds
    yp_2025 = YearProceeds(
        daily={},
        monthly={
            date(2025, 3, 31): MonthProceeds(
                btc_sold_per_share=Decimal("0.00000020"),
                proceeds_per_share_usd=Decimal("0.01509769"),
            ),
        },
        source="test2.pdf",
    )
    proceeds_db.save(project_dir, 2025, yp_2025)

    # Compute 2025 — should load prior state from 2024
    result = runner.invoke(
        cli, ["--project", str(project_dir), "compute", "--year", "2025"]
    )
    assert result.exit_code == 0, result.output
    assert "Computed 2025" in result.output


def test_compute_value_error_wrapped(project_dir, tmp_path):
    """ValueError from compute_year should be wrapped in ClickException."""
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project", str(project_dir), "import-trades", "--file", str(csv_path)]
    )
    assert result.exit_code == 0, result.output

    with patch(
        "fbtc_taxgrinder.cli.commands.compute_year",
        side_effect=ValueError("test error"),
    ):
        result = runner.invoke(
            cli, ["--project", str(project_dir), "compute", "--year", "2024"]
        )
    assert result.exit_code != 0
    assert "test error" in result.output


def test_lots_empty(project_dir):
    """lots command with no data shows 'No lots found'."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--project", str(project_dir), "lots"])
    assert result.exit_code == 0
    assert "No lots" in result.output


def test_lots_with_sell_events(project_dir, tmp_path):
    """lots command displays sell events."""
    _save_test_proceeds(project_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv_with_sell(csv_path)

    runner = CliRunner()
    result = runner.invoke(
        cli, ["--project", str(project_dir), "import-trades", "--file", str(csv_path)]
    )
    assert result.exit_code == 0, result.output
    result = runner.invoke(cli, ["--project", str(project_dir), "lots"])
    assert result.exit_code == 0
    assert "lot-1" in result.output
    assert "sell" in result.output


def test_status_no_directories(project_dir):
    """status command when proceeds/results dirs don't exist."""
    import shutil

    # Remove the dirs that conftest created, then also patch cli to not recreate them
    shutil.rmtree(project_dir / "proceeds")
    shutil.rmtree(project_dir / "results")

    # Directly invoke the status command with a pre-set context to bypass cli group
    from fbtc_taxgrinder.cli.commands import status

    runner = CliRunner()
    result = runner.invoke(status, [], obj={"project_dir": project_dir})
    assert result.exit_code == 0
    assert "Proceeds: none" in result.output
    assert "Computed: none" in result.output


def test_int_stems_non_numeric(tmp_path):
    """_int_stems should skip non-numeric JSON filenames."""
    from fbtc_taxgrinder.cli.commands import _int_stems

    d = tmp_path / "test_stems"
    d.mkdir()
    (d / "2024.json").write_text("{}")
    (d / "notes.json").write_text("{}")
    (d / "backup.json").write_text("{}")
    result = _int_stems(d)
    assert result == [2024]


def test_e2e_workflow(project_dir, tmp_path):
    """Full workflow: seed proceeds, import trades, compute, export, re-compute."""
    runner = CliRunner()

    # Manually seed proceeds (skip PDF parsing for this test)
    _save_test_proceeds(project_dir)

    # Create a minimal ETrade CSV
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    # Import trades
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "import-trades",
            "--file",
            str(csv_path),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "1 new lots" in result.output

    # Compute
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "compute",
            "--year",
            "2024",
        ],
    )
    assert result.exit_code == 0, result.output

    # Export
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "export",
            "--year",
            "2024",
        ],
    )
    assert result.exit_code == 0, result.output
    assert (project_dir / "output" / "2024_monthly.csv").exists()
    assert (project_dir / "output" / "2024_summary.csv").exists()

    # Verify skip on re-compute
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "compute",
            "--year",
            "2024",
        ],
    )
    assert "already computed" in result.output

    # Verify --force recomputes
    result = runner.invoke(
        cli,
        [
            "--project",
            str(project_dir),
            "compute",
            "--year",
            "2024",
            "--force",
        ],
    )
    assert result.exit_code == 0

import csv
import json
from decimal import Decimal
from datetime import date
from pathlib import Path
from unittest.mock import patch, MagicMock

from click.testing import CliRunner
from fbtc_taxgrinder.cli.commands import cli
from fbtc_taxgrinder.db import proceeds as proceeds_db
from fbtc_taxgrinder.db import lots as lots_db
from fbtc_taxgrinder.models import MonthProceeds, YearProceeds, Lot


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
        "Trade Date", "Order Type", "Security", "Cusip",
        "Transaction Description", "Quantity", "Executed Price",
        "Commission", "Net Amount",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerow({
            "Trade Date": "1/25/2024", "Order Type": "Buy", "Security": "FBTC",
            "Cusip": "315948109", "Transaction Description": "FBTC",
            "Quantity": "204", "Executed Price": "34.81",
            "Commission": "0.00", "Net Amount": "7101.24",
        })


# --- Error path tests ---

def test_import_proceeds_missing_file(data_dir):
    """import-proceeds --file with nonexistent file should error."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "import-proceeds", "--file", "/nonexistent.pdf",
    ])
    assert result.exit_code != 0
    assert "not found" in result.output.lower() or "error" in result.output.lower()


def test_import_proceeds_no_source(data_dir):
    """import-proceeds without --url or --file should error."""
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "import-proceeds",
    ])
    assert result.exit_code != 0


def test_compute_missing_proceeds(data_dir):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "compute", "--year", "2024",
    ])
    assert result.exit_code != 0


def test_export_missing_results(data_dir):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "export", "--year", "2024", "--output", str(data_dir / "out"),
    ])
    assert result.exit_code != 0
    assert "No results" in result.output


# --- Happy path tests ---

def test_import_proceeds_from_file(data_dir):
    """import-proceeds --file with a mocked PDF parser."""
    mock_yp = YearProceeds(
        daily={date(2024, 1, 11): Decimal("0.00087448")},
        monthly={},
        source="test.pdf",
    )
    with patch("fbtc_taxgrinder.cli.commands.parse_fidelity_pdf_file", return_value=mock_yp):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--data-dir", str(data_dir),
            "import-proceeds", "--file", __file__,  # use any existing file
        ])
    assert result.exit_code == 0
    assert "Imported 2024" in result.output


def test_import_proceeds_from_url(data_dir):
    """import-proceeds --url with a mocked PDF parser."""
    mock_yp = YearProceeds(
        daily={date(2024, 1, 11): Decimal("0.00087448")},
        monthly={},
        source="test.pdf",
    )
    with patch("fbtc_taxgrinder.cli.commands.parse_fidelity_pdf_url", return_value=mock_yp):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--data-dir", str(data_dir),
            "import-proceeds", "--url", "https://example.com/test.pdf",
        ])
    assert result.exit_code == 0
    assert "Imported 2024" in result.output


def test_import_proceeds_idempotent(data_dir):
    """Second import of same year should skip."""
    _save_test_proceeds(data_dir)
    mock_yp = YearProceeds(
        daily={date(2024, 1, 25): Decimal("0.00087448")},
        monthly={},
        source="test2.pdf",
    )
    with patch("fbtc_taxgrinder.cli.commands.parse_fidelity_pdf_file", return_value=mock_yp):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--data-dir", str(data_dir),
            "import-proceeds", "--file", __file__,
        ])
    assert result.exit_code == 0
    assert "already imported" in result.output


def test_import_proceeds_empty_pdf(data_dir):
    """PDF with no data should error."""
    mock_yp = YearProceeds(daily={}, monthly={}, source="empty.pdf")
    with patch("fbtc_taxgrinder.cli.commands.parse_fidelity_pdf_file", return_value=mock_yp):
        runner = CliRunner()
        result = runner.invoke(cli, [
            "--data-dir", str(data_dir),
            "import-proceeds", "--file", __file__,
        ])
    assert result.exit_code != 0
    assert "No data" in result.output


def test_import_trades(data_dir, tmp_path):
    """Full import-trades happy path."""
    _save_test_proceeds(data_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "import-trades", "--file", str(csv_path),
    ])
    assert result.exit_code == 0
    assert "1 new lots" in result.output


def test_import_trades_missing_file(data_dir):
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "import-trades", "--file", "/nonexistent.csv",
    ])
    assert result.exit_code != 0


def test_import_trades_missing_proceeds(data_dir, tmp_path):
    """import-trades without proceeds should error."""
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "import-trades", "--file", str(csv_path),
    ])
    assert result.exit_code != 0
    assert "not imported" in result.output.lower() or "import-proceeds" in result.output


def test_compute_happy_path(data_dir, tmp_path):
    """Full compute happy path."""
    _save_test_proceeds(data_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    # Import trades first
    runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "import-trades", "--file", str(csv_path),
    ])
    # Compute
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "compute", "--year", "2024",
    ])
    assert result.exit_code == 0
    assert "Computed 2024" in result.output


def test_compute_already_exists(data_dir, tmp_path):
    """Compute without --force when results exist should skip."""
    _save_test_proceeds(data_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "import-trades", "--file", str(csv_path),
    ])
    runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "compute", "--year", "2024",
    ])
    # Second compute should skip
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "compute", "--year", "2024",
    ])
    assert result.exit_code == 0
    assert "already computed" in result.output


def test_compute_no_lots(data_dir):
    """Compute without lots should error."""
    _save_test_proceeds(data_dir)
    runner = CliRunner()
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "compute", "--year", "2024",
    ])
    assert result.exit_code != 0
    assert "No lots" in result.output


def test_export_happy_path(data_dir, tmp_path):
    """Full export happy path."""
    _save_test_proceeds(data_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    runner.invoke(cli, ["--data-dir", str(data_dir), "import-trades", "--file", str(csv_path)])
    runner.invoke(cli, ["--data-dir", str(data_dir), "compute", "--year", "2024"])

    out_dir = tmp_path / "export"
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "export", "--year", "2024", "--output", str(out_dir),
    ])
    assert result.exit_code == 0
    assert "Exported" in result.output
    assert (out_dir / "2024_monthly.csv").exists()


def test_lots_with_data(data_dir, tmp_path):
    """lots command with imported data."""
    _save_test_proceeds(data_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    runner.invoke(cli, ["--data-dir", str(data_dir), "import-trades", "--file", str(csv_path)])
    result = runner.invoke(cli, ["--data-dir", str(data_dir), "lots"])
    assert result.exit_code == 0
    assert "lot-1" in result.output
    assert "204" in result.output


def test_status_empty(data_dir):
    runner = CliRunner()
    result = runner.invoke(cli, ["--data-dir", str(data_dir), "status"])
    assert result.exit_code == 0
    assert "0 lots" in result.output


def test_status_with_data(data_dir, tmp_path):
    """status command with imported data."""
    _save_test_proceeds(data_dir)
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    runner = CliRunner()
    runner.invoke(cli, ["--data-dir", str(data_dir), "import-trades", "--file", str(csv_path)])
    runner.invoke(cli, ["--data-dir", str(data_dir), "compute", "--year", "2024"])

    result = runner.invoke(cli, ["--data-dir", str(data_dir), "status"])
    assert result.exit_code == 0
    assert "1 lots" in result.output
    assert "2024" in result.output


def test_e2e_workflow(data_dir, tmp_path):
    """Full workflow: seed proceeds, import trades, compute, export, re-compute."""
    runner = CliRunner()

    # Manually seed proceeds (skip PDF parsing for this test)
    _save_test_proceeds(data_dir)

    # Create a minimal ETrade CSV
    csv_path = tmp_path / "trades.csv"
    _write_etrade_csv(csv_path)

    # Import trades
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "import-trades", "--file", str(csv_path),
    ])
    assert result.exit_code == 0, result.output
    assert "1 new lots" in result.output

    # Compute
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "compute", "--year", "2024",
    ])
    assert result.exit_code == 0, result.output

    # Export
    output_dir = tmp_path / "output"
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "export", "--year", "2024", "--format", "csv",
        "--output", str(output_dir),
    ])
    assert result.exit_code == 0, result.output
    assert (output_dir / "2024_monthly.csv").exists()
    assert (output_dir / "2024_summary.csv").exists()

    # Verify skip on re-compute
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "compute", "--year", "2024",
    ])
    assert "already computed" in result.output

    # Verify --force recomputes
    result = runner.invoke(cli, [
        "--data-dir", str(data_dir),
        "compute", "--year", "2024", "--force",
    ])
    assert result.exit_code == 0

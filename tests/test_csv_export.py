"""Tests for CSV export functionality."""

import csv
from datetime import date
from decimal import Decimal

from fbtc_taxgrinder.export.csv_export import export_year_csv
from fbtc_taxgrinder.models import Disposition, ExpenseResult, HoldingTerm, YearResult


def test_export_creates_three_files(tmp_path):
    """Export creates monthly, dispositions, and summary CSVs with correct data."""
    yr = YearResult(
        year=2024,
        lot_results={
            "lot-1": [
                ExpenseResult(
                    sell_date=date(2024, 8, 31),
                    days_held=Decimal("31"),
                    days_in_month=Decimal("31"),
                    shares=Decimal("204"),
                    total_btc_sold=Decimal("0.00003672"),
                    cost_basis_of_sold=Decimal("1.46"),
                    total_expense=Decimal("2.18"),
                    gain_loss=Decimal("0.72"),
                    adj_btc=Decimal("0.17835720"),
                    adj_basis=Decimal("7099.78"),
                    holding_term=HoldingTerm.LONG_TERM,
                ),
            ],
        },
        dispositions=[
            Disposition(
                lot_id="lot-1",
                disposition_id="lot-1-sell-1",
                date_sold=date(2024, 12, 23),
                shares_sold=Decimal("14"),
                proceeds=Decimal("1067.08"),
                disposed_btc=Decimal("0.012"),
                disposed_basis=Decimal("487.12"),
                gain_loss=Decimal("579.96"),
            ),
        ],
        end_states={},
        total_investment_expense=Decimal("2.18"),
        total_reportable_gain=Decimal("0.72"),
        total_cost_basis_of_expense=Decimal("1.46"),
    )
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    export_year_csv(yr, output_dir)

    monthly_path = output_dir / "2024_monthly.csv"
    dispositions_path = output_dir / "2024_dispositions.csv"
    summary_path = output_dir / "2024_summary.csv"

    assert monthly_path.exists()
    assert dispositions_path.exists()
    assert summary_path.exists()

    with open(monthly_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["lot_id"] == "lot-1"
        assert rows[0]["sell_date"] == "2024-08-31"

    with open(dispositions_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["disposition_id"] == "lot-1-sell-1"

    with open(summary_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 2  # 1 sell-date row + 1 total row
        # Sell-date row
        assert rows[0]["sell_date"] == "2024-08-31"
        assert rows[0]["investment_expense"] == "2.18"
        assert rows[0]["cost_basis_of_expense"] == "1.46"
        assert rows[0]["reportable_gain"] == "0.72"
        # Total row
        assert rows[1]["sell_date"] == "total"
        assert rows[1]["investment_expense"] == "2.18"


def test_summary_aggregates_across_lots(tmp_path):
    """Summary rows sum values across all lots for the same sell date."""
    er_kwargs = {
        "sell_date": date(2024, 8, 31),
        "days_held": Decimal("31"),
        "days_in_month": Decimal("31"),
        "shares": Decimal("100"),
        "total_btc_sold": Decimal("0.0001"),
        "adj_btc": Decimal("0.5"),
        "adj_basis": Decimal("1000"),
        "holding_term": HoldingTerm.LONG_TERM,
    }
    yr = YearResult(
        year=2024,
        lot_results={
            "lot-1": [
                ExpenseResult(
                    cost_basis_of_sold=Decimal("1.00"),
                    total_expense=Decimal("2.00"),
                    gain_loss=Decimal("3.00"),
                    **er_kwargs,
                )
            ],
            "lot-2": [
                ExpenseResult(
                    cost_basis_of_sold=Decimal("4.00"),
                    total_expense=Decimal("5.00"),
                    gain_loss=Decimal("6.00"),
                    **er_kwargs,
                )
            ],
        },
        dispositions=[],
        end_states={},
        total_investment_expense=Decimal("7.00"),
        total_reportable_gain=Decimal("9.00"),
        total_cost_basis_of_expense=Decimal("5.00"),
    )
    export_year_csv(yr, tmp_path)
    with open(tmp_path / "2024_summary.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["sell_date"] == "2024-08-31"
    assert rows[0]["investment_expense"] == "7.00"
    assert rows[0]["cost_basis_of_expense"] == "5.00"
    assert rows[0]["reportable_gain"] == "9.00"


def test_summary_rounds_to_cents(tmp_path):
    """Summary values are rounded to cents using ROUND_HALF_UP."""
    er_kwargs = {
        "sell_date": date(2024, 8, 31),
        "days_held": Decimal("31"),
        "days_in_month": Decimal("31"),
        "shares": Decimal("100"),
        "total_btc_sold": Decimal("0.0001"),
        "adj_btc": Decimal("0.5"),
        "adj_basis": Decimal("1000"),
        "holding_term": HoldingTerm.LONG_TERM,
    }
    yr = YearResult(
        year=2024,
        lot_results={
            "lot-1": [
                ExpenseResult(
                    cost_basis_of_sold=Decimal("1.234"),
                    total_expense=Decimal("2.185"),
                    gain_loss=Decimal("0.9551"),
                    **er_kwargs,
                )
            ],
        },
        dispositions=[],
        end_states={},
        total_investment_expense=Decimal("2.185"),
        total_reportable_gain=Decimal("0.9551"),
        total_cost_basis_of_expense=Decimal("1.234"),
    )
    export_year_csv(yr, tmp_path)
    with open(tmp_path / "2024_summary.csv", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    assert rows[0]["investment_expense"] == "2.19"
    assert rows[0]["cost_basis_of_expense"] == "1.23"
    assert rows[0]["reportable_gain"] == "0.96"
    assert rows[1]["investment_expense"] == "2.19"
    assert rows[1]["cost_basis_of_expense"] == "1.23"
    assert rows[1]["reportable_gain"] == "0.96"

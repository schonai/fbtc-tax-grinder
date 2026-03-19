import csv
from decimal import Decimal
from datetime import date
from pathlib import Path
from fbtc_taxgrinder.models import MonthResult, Disposition, YearResult
from fbtc_taxgrinder.export.csv_export import export_year_csv


def test_export_creates_three_files(tmp_path):
    yr = YearResult(
        year=2024,
        lot_results={
            "lot-1": [
                MonthResult(
                    month=8, days_held=Decimal("31"), days_in_month=Decimal("31"),
                    shares=Decimal("204"), total_btc_sold=Decimal("0.00003672"),
                    cost_basis_of_sold=Decimal("1.46"),
                    total_expense=Decimal("2.18"),
                    gain_loss=Decimal("0.72"),
                    adj_btc=Decimal("0.17835720"),
                    adj_basis=Decimal("7099.78"),
                ),
            ],
        },
        dispositions=[
            Disposition(
                lot_id="lot-1", disposition_id="lot-1-sell-1",
                date_sold=date(2024, 12, 23), shares_sold=Decimal("14"),
                proceeds=Decimal("1067.08"), disposed_btc=Decimal("0.012"),
                disposed_basis=Decimal("487.12"), gain_loss=Decimal("579.96"),
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

    with open(monthly_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["lot_id"] == "lot-1"
        assert rows[0]["month"] == "8"

    with open(dispositions_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["disposition_id"] == "lot-1-sell-1"

    with open(summary_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["total_investment_expense"] == "2.18"

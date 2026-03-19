from __future__ import annotations

import csv
from pathlib import Path

from fbtc_taxgrinder.models import YearResult


def export_year_csv(year_result: YearResult, output_dir: Path) -> None:
    """Export year results to three CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    year = year_result.year

    # Monthly breakdown
    monthly_path = output_dir / f"{year}_monthly.csv"
    with open(monthly_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "lot_id", "month", "days_held", "days_in_month", "shares",
            "total_btc_sold", "cost_basis_of_sold", "total_expense",
            "gain_loss", "adj_btc", "adj_basis",
        ])
        for lot_id, results in sorted(year_result.lot_results.items()):
            for mr in results:
                writer.writerow([
                    lot_id, mr.month, mr.days_held, mr.days_in_month,
                    mr.shares, mr.total_btc_sold, mr.cost_basis_of_sold,
                    mr.total_expense, mr.gain_loss, mr.adj_btc, mr.adj_basis,
                ])

    # Dispositions
    disp_path = output_dir / f"{year}_dispositions.csv"
    with open(disp_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "lot_id", "disposition_id", "date_sold", "shares_sold",
            "proceeds", "disposed_btc", "disposed_basis", "gain_loss",
        ])
        for d in year_result.dispositions:
            writer.writerow([
                d.lot_id, d.disposition_id, d.date_sold.isoformat(),
                d.shares_sold, d.proceeds, d.disposed_btc,
                d.disposed_basis, d.gain_loss,
            ])

    # Annual summary
    summary_path = output_dir / f"{year}_summary.csv"
    with open(summary_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "year", "total_investment_expense", "total_reportable_gain",
            "total_cost_basis_of_expense",
        ])
        writer.writerow([
            year, year_result.total_investment_expense,
            year_result.total_reportable_gain,
            year_result.total_cost_basis_of_expense,
        ])

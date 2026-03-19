from __future__ import annotations

import csv
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

CENTS = Decimal("0.01")

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

    # Summary: monthly aggregates + annual total
    monthly_agg: dict[int, dict[str, Decimal]] = defaultdict(
        lambda: {"investment_expense": Decimal(0), "cost_basis_of_expense": Decimal(0), "reportable_gain": Decimal(0)}
    )
    for results in year_result.lot_results.values():
        for mr in results:
            monthly_agg[mr.month]["investment_expense"] += mr.total_expense
            monthly_agg[mr.month]["cost_basis_of_expense"] += mr.cost_basis_of_sold
            monthly_agg[mr.month]["reportable_gain"] += mr.gain_loss

    summary_path = output_dir / f"{year}_summary.csv"
    with open(summary_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([
            "month", "investment_expense", "cost_basis_of_expense",
            "reportable_gain",
        ])
        for month in sorted(monthly_agg):
            agg = monthly_agg[month]
            writer.writerow([
                month,
                agg["investment_expense"].quantize(CENTS, ROUND_HALF_UP),
                agg["cost_basis_of_expense"].quantize(CENTS, ROUND_HALF_UP),
                agg["reportable_gain"].quantize(CENTS, ROUND_HALF_UP),
            ])
        writer.writerow([
            "total",
            year_result.total_investment_expense.quantize(CENTS, ROUND_HALF_UP),
            year_result.total_cost_basis_of_expense.quantize(CENTS, ROUND_HALF_UP),
            year_result.total_reportable_gain.quantize(CENTS, ROUND_HALF_UP),
        ])

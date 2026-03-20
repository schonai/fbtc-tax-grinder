"""CSV export for yearly WHFIT tax lot results."""

from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from fbtc_taxgrinder.models import YearResult

CENTS = Decimal("0.01")


def export_year_csv(year_result: YearResult, output_dir: Path) -> None:
    """Export year results to three CSV files."""
    output_dir.mkdir(parents=True, exist_ok=True)
    year = year_result.year

    # Monthly breakdown
    monthly_path = output_dir / f"{year}_monthly.csv"
    with open(monthly_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
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
                    ]
                )

    # Dispositions
    disp_path = output_dir / f"{year}_dispositions.csv"
    with open(disp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "lot_id",
                "disposition_id",
                "date_sold",
                "shares_sold",
                "proceeds",
                "disposed_btc",
                "disposed_basis",
                "gain_loss",
            ]
        )
        for d in year_result.dispositions:
            writer.writerow(
                [
                    d.lot_id,
                    d.disposition_id,
                    d.date_sold.isoformat(),
                    d.shares_sold,
                    d.proceeds,
                    d.disposed_btc,
                    d.disposed_basis,
                    d.gain_loss,
                ]
            )

    # Summary: per-sell-date aggregates + annual total
    date_agg: dict[date, dict[str, Decimal]] = defaultdict(
        lambda: {
            "investment_expense": Decimal("0"),
            "cost_basis_of_expense": Decimal("0"),
            "reportable_gain": Decimal("0"),
        }
    )
    for results in year_result.lot_results.values():
        for er in results:
            date_agg[er.sell_date]["investment_expense"] += er.total_expense
            date_agg[er.sell_date]["cost_basis_of_expense"] += er.cost_basis_of_sold
            date_agg[er.sell_date]["reportable_gain"] += er.gain_loss

    summary_path = output_dir / f"{year}_summary.csv"
    with open(summary_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "sell_date",
                "investment_expense",
                "cost_basis_of_expense",
                "reportable_gain",
            ]
        )
        for sell_date in sorted(date_agg):
            agg = date_agg[sell_date]
            writer.writerow(
                [
                    sell_date.isoformat(),
                    agg["investment_expense"].quantize(CENTS, ROUND_HALF_UP),
                    agg["cost_basis_of_expense"].quantize(CENTS, ROUND_HALF_UP),
                    agg["reportable_gain"].quantize(CENTS, ROUND_HALF_UP),
                ]
            )
        writer.writerow(
            [
                "total",
                year_result.total_investment_expense.quantize(CENTS, ROUND_HALF_UP),
                year_result.total_cost_basis_of_expense.quantize(CENTS, ROUND_HALF_UP),
                year_result.total_reportable_gain.quantize(CENTS, ROUND_HALF_UP),
            ]
        )

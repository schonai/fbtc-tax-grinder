from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from fbtc_taxgrinder.models import Disposition, LotState, MonthResult, YearResult


def save(data_dir: Path, yr: YearResult) -> None:
    path = data_dir / "results" / f"{yr.year}.json"
    data = {
        "year": yr.year,
        "end_states": {
            lot_id: {
                "adj_btc": str(s.adj_btc),
                "adj_basis": str(s.adj_basis),
                "shares": str(s.shares),
            }
            for lot_id, s in yr.end_states.items()
        },
        "lot_results": {
            lot_id: [
                {
                    "month": mr.month,
                    "days_held": str(mr.days_held),
                    "days_in_month": str(mr.days_in_month),
                    "shares": str(mr.shares),
                    "total_btc_sold": str(mr.total_btc_sold),
                    "cost_basis_of_sold": str(mr.cost_basis_of_sold),
                    "total_expense": str(mr.total_expense),
                    "gain_loss": str(mr.gain_loss),
                    "adj_btc": str(mr.adj_btc),
                    "adj_basis": str(mr.adj_basis),
                }
                for mr in month_results
            ]
            for lot_id, month_results in yr.lot_results.items()
        },
        "dispositions": [
            {
                "lot_id": d.lot_id,
                "disposition_id": d.disposition_id,
                "date_sold": d.date_sold.isoformat(),
                "shares_sold": str(d.shares_sold),
                "proceeds": str(d.proceeds),
                "disposed_btc": str(d.disposed_btc),
                "disposed_basis": str(d.disposed_basis),
                "gain_loss": str(d.gain_loss),
            }
            for d in yr.dispositions
        ],
        "total_investment_expense": str(yr.total_investment_expense),
        "total_reportable_gain": str(yr.total_reportable_gain),
        "total_cost_basis_of_expense": str(yr.total_cost_basis_of_expense),
    }
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def load(data_dir: Path, year: int) -> YearResult | None:
    path = data_dir / "results" / f"{year}.json"
    if not path.exists():
        return None
    with open(path) as f:
        data = json.load(f)
    lot_results = {
        lot_id: [
            MonthResult(
                month=mr["month"],
                days_held=Decimal(mr["days_held"]),
                days_in_month=Decimal(mr["days_in_month"]),
                shares=Decimal(mr["shares"]),
                total_btc_sold=Decimal(mr["total_btc_sold"]),
                cost_basis_of_sold=Decimal(mr["cost_basis_of_sold"]),
                total_expense=Decimal(mr["total_expense"]),
                gain_loss=Decimal(mr["gain_loss"]),
                adj_btc=Decimal(mr["adj_btc"]),
                adj_basis=Decimal(mr["adj_basis"]),
            )
            for mr in month_results
        ]
        for lot_id, month_results in data["lot_results"].items()
    }
    dispositions = [
        Disposition(
            lot_id=d["lot_id"],
            disposition_id=d["disposition_id"],
            date_sold=date.fromisoformat(d["date_sold"]),
            shares_sold=Decimal(d["shares_sold"]),
            proceeds=Decimal(d["proceeds"]),
            disposed_btc=Decimal(d["disposed_btc"]),
            disposed_basis=Decimal(d["disposed_basis"]),
            gain_loss=Decimal(d["gain_loss"]),
        )
        for d in data["dispositions"]
    ]
    end_states = {
        lot_id: LotState(
            adj_btc=Decimal(v["adj_btc"]),
            adj_basis=Decimal(v["adj_basis"]),
            shares=Decimal(v["shares"]),
        )
        for lot_id, v in data.get("end_states", {}).items()
    }
    return YearResult(
        year=data["year"],
        lot_results=lot_results,
        dispositions=dispositions,
        end_states=end_states,
        total_investment_expense=Decimal(data["total_investment_expense"]),
        total_reportable_gain=Decimal(data["total_reportable_gain"]),
        total_cost_basis_of_expense=Decimal(data["total_cost_basis_of_expense"]),
    )

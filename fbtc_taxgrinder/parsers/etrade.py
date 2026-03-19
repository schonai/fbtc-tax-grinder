from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal


def parse_etrade_csv(file_path: str) -> dict:
    """Parse an ETrade CSV file and extract FBTC transactions.

    Returns dict with 'buys' and 'sells' lists, each sorted by date.
    Each buy: {date, shares, price_per_share, total_cost}
    Each sell: {date, shares, price_per_share, proceeds}
    """
    buys: list[dict] = []
    sells: list[dict] = []

    with open(file_path, newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row["Security"].strip() != "FBTC":
                continue

            parts = row["Trade Date"].strip().split("/")
            trade_date = date(int(parts[2]), int(parts[0]), int(parts[1]))
            shares = Decimal(row["Quantity"].strip())
            price = Decimal(row["Executed Price"].strip())
            order_type = row["Order Type"].strip()

            if order_type == "Buy":
                net_amount = Decimal(row["Net Amount"].strip())
                buys.append({
                    "date": trade_date,
                    "shares": shares,
                    "price_per_share": price,
                    "total_cost": net_amount,
                })
            elif order_type == "Sell":
                proceeds = Decimal(row["Net Amount"].strip())
                sells.append({
                    "date": trade_date,
                    "shares": shares,
                    "price_per_share": price,
                    "proceeds": proceeds,
                })

    buys.sort(key=lambda x: x["date"])
    sells.sort(key=lambda x: x["date"])

    return {"buys": buys, "sells": sells}

"""ETrade CSV parser for FBTC buy/sell transactions."""

from __future__ import annotations

import csv
import itertools
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from pathlib import Path


@dataclass
class BuyTrade:
    """A parsed buy transaction from ETrade."""

    date: date
    shares: Decimal
    price_per_share: Decimal
    total_cost: Decimal


@dataclass
class SellTrade:
    """A parsed sell transaction from ETrade."""

    date: date
    shares: Decimal
    price_per_share: Decimal
    proceeds: Decimal


@dataclass
class TradeResult:
    """Parsed buy and sell trades from an ETrade CSV."""

    buys: list[BuyTrade]
    sells: list[SellTrade]


def parse_etrade_rows(rows: Iterable[dict]) -> TradeResult:
    """Extract FBTC transactions from ETrade CSV row dicts.

    Args:
        rows: Iterable of dicts with keys matching ETrade CSV headers.

    Returns:
        TradeResult with buys and sells lists, each sorted by date.
    """
    buys: list[BuyTrade] = []
    sells: list[SellTrade] = []

    rows_iter = iter(rows)
    first = next(rows_iter, None)
    if first is None:
        return TradeResult(buys=[], sells=[])
    required = {
        "Security",
        "Trade Date",
        "Quantity",
        "Executed Price",
        "Order Type",
        "Net Amount",
    }
    missing = required - first.keys()
    if missing:
        raise ValueError(f"Missing required column(s): {', '.join(sorted(missing))}")

    for row in itertools.chain([first], rows_iter):
        if row["Security"].strip() != "FBTC":
            continue

        parts = row["Trade Date"].strip().split("/")
        trade_date = date(int(parts[2]), int(parts[0]), int(parts[1]))
        shares = Decimal(row["Quantity"].strip())
        price = Decimal(row["Executed Price"].strip())
        order_type = row["Order Type"].strip()

        if order_type == "Buy":
            net_amount = Decimal(row["Net Amount"].strip())
            buys.append(
                BuyTrade(
                    date=trade_date,
                    shares=shares,
                    price_per_share=price,
                    total_cost=net_amount,
                )
            )
        elif order_type == "Sell":
            proceeds = Decimal(row["Net Amount"].strip())
            sells.append(
                SellTrade(
                    date=trade_date,
                    shares=shares,
                    price_per_share=price,
                    proceeds=proceeds,
                )
            )

    buys.sort(key=lambda x: x.date)
    sells.sort(key=lambda x: x.date)

    return TradeResult(buys=buys, sells=sells)


def parse_etrade_csv(file_path: str | Path) -> TradeResult:
    """Parse an ETrade CSV file and extract FBTC transactions.

    Args:
        file_path: Path to the ETrade CSV file.

    Returns:
        TradeResult with buys and sells lists, each sorted by date.
    """
    with open(file_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return parse_etrade_rows(reader)

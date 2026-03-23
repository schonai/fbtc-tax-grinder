"""Tests for ETrade CSV parser."""

import csv
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from fbtc_taxgrinder.parsers.etrade import parse_etrade_csv, parse_etrade_rows


def _write_csv(path: Path, rows: list[dict]):
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
        writer.writerows(rows)


def test_parse_rows_buys_only():
    """Test pure logic function with in-memory row dicts."""
    rows = [
        {
            "Trade Date": "1/25/2024",
            "Order Type": "Buy",
            "Security": "FBTC",
            "Quantity": "204",
            "Executed Price": "34.81",
            "Net Amount": "7101.24",
        },
        {
            "Trade Date": "1/25/2024",
            "Order Type": "Buy",
            "Security": "VOO",
            "Quantity": "10",
            "Executed Price": "400.00",
            "Net Amount": "4000.00",
        },
    ]
    result = parse_etrade_rows(rows)
    assert len(result.buys) == 1
    assert result.buys[0].date == date(2024, 1, 25)
    assert result.buys[0].shares == Decimal("204")
    assert result.buys[0].price_per_share == Decimal("34.81")
    assert result.buys[0].total_cost == Decimal("7101.24")
    assert len(result.sells) == 0


def test_parse_rows_sells():
    """Test pure logic function with sell rows."""
    rows = [
        {
            "Trade Date": "12/23/2025",
            "Order Type": "Sell",
            "Security": "FBTC",
            "Quantity": "14",
            "Executed Price": "76.2201",
            "Net Amount": "1067.08",
        },
    ]
    result = parse_etrade_rows(rows)
    assert len(result.sells) == 1
    assert result.sells[0].date == date(2025, 12, 23)
    assert result.sells[0].shares == Decimal("14")
    assert result.sells[0].proceeds == Decimal("1067.08")


def test_parse_rows_chronological_order():
    """Buys and sells should be sorted by date regardless of input order."""
    rows = [
        {
            "Trade Date": "12/23/2025",
            "Order Type": "Sell",
            "Security": "FBTC",
            "Quantity": "14",
            "Executed Price": "76.00",
            "Net Amount": "1064.00",
        },
        {
            "Trade Date": "1/25/2024",
            "Order Type": "Buy",
            "Security": "FBTC",
            "Quantity": "204",
            "Executed Price": "34.81",
            "Net Amount": "7101.24",
        },
    ]
    result = parse_etrade_rows(rows)
    assert result.buys[0].date == date(2024, 1, 25)
    assert result.sells[0].date == date(2025, 12, 23)


def test_parse_etrade_csv(tmp_path):
    """Test file I/O wrapper delegates correctly."""
    csv_path = tmp_path / "trades.csv"
    _write_csv(
        csv_path,
        [
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
            },
        ],
    )
    result = parse_etrade_csv(str(csv_path))
    assert len(result.buys) == 1
    assert result.buys[0].date == date(2024, 1, 25)


def test_parse_rows_empty():
    """Empty input returns empty TradeResult."""
    result = parse_etrade_rows([])
    assert not result.buys
    assert not result.sells


def test_parse_rows_missing_columns():
    """Missing required columns should raise ValueError."""
    rows = [
        {
            "Trade Date": "1/25/2024",
            "Order Type": "Buy",
            "Security": "FBTC",
            # Missing Quantity, Executed Price, Net Amount
        },
    ]
    with pytest.raises(ValueError, match="Missing required column"):
        parse_etrade_rows(rows)

import csv
from decimal import Decimal
from datetime import date
from pathlib import Path
from fbtc_taxgrinder.parsers.etrade import parse_etrade_csv


def _write_csv(path: Path, rows: list[dict]):
    fieldnames = [
        "Trade Date", "Order Type", "Security", "Cusip",
        "Transaction Description", "Quantity", "Executed Price",
        "Commission", "Net Amount",
    ]
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_parse_buys_only(tmp_path):
    csv_path = tmp_path / "trades.csv"
    _write_csv(csv_path, [
        {
            "Trade Date": "1/25/2024", "Order Type": "Buy", "Security": "FBTC",
            "Cusip": "315948109", "Transaction Description": "FIDELITY WISE ORIGIN BITCOIN",
            "Quantity": "204", "Executed Price": "34.81",
            "Commission": "0.0000", "Net Amount": "7101.24",
        },
        {
            "Trade Date": "1/25/2024", "Order Type": "Buy", "Security": "VOO",
            "Cusip": "922908363", "Transaction Description": "VANGUARD S&P 500 ETF",
            "Quantity": "10", "Executed Price": "400.00",
            "Commission": "0.00", "Net Amount": "4000.00",
        },
    ])
    result = parse_etrade_csv(str(csv_path))
    assert len(result["buys"]) == 1
    assert result["buys"][0]["date"] == date(2024, 1, 25)
    assert result["buys"][0]["shares"] == Decimal("204")
    assert result["buys"][0]["price_per_share"] == Decimal("34.81")
    assert result["buys"][0]["total_cost"] == Decimal("7101.24")
    assert len(result["sells"]) == 0


def test_parse_sells(tmp_path):
    csv_path = tmp_path / "trades.csv"
    _write_csv(csv_path, [
        {
            "Trade Date": "12/23/2025", "Order Type": "Sell", "Security": "FBTC",
            "Cusip": "315948109",
            "Transaction Description": "FIDELITY WISE ORIGIN BITCOIN UNSOLICITED TRADE",
            "Quantity": "14", "Executed Price": "76.2201",
            "Commission": "0.0000", "Net Amount": "1067.08",
        },
    ])
    result = parse_etrade_csv(str(csv_path))
    assert len(result["sells"]) == 1
    assert result["sells"][0]["date"] == date(2025, 12, 23)
    assert result["sells"][0]["shares"] == Decimal("14")
    assert result["sells"][0]["price_per_share"] == Decimal("76.2201")
    assert result["sells"][0]["proceeds"] == Decimal("1067.08")


def test_chronological_order(tmp_path):
    csv_path = tmp_path / "trades.csv"
    _write_csv(csv_path, [
        {
            "Trade Date": "12/23/2025", "Order Type": "Sell", "Security": "FBTC",
            "Cusip": "315948109", "Transaction Description": "FBTC",
            "Quantity": "14", "Executed Price": "76.00",
            "Commission": "0.00", "Net Amount": "1064.00",
        },
        {
            "Trade Date": "1/25/2024", "Order Type": "Buy", "Security": "FBTC",
            "Cusip": "315948109", "Transaction Description": "FBTC",
            "Quantity": "204", "Executed Price": "34.81",
            "Commission": "0.00", "Net Amount": "7101.24",
        },
    ])
    result = parse_etrade_csv(str(csv_path))
    # Buys and sells should each be sorted by date
    assert result["buys"][0]["date"] == date(2024, 1, 25)
    assert result["sells"][0]["date"] == date(2025, 12, 23)

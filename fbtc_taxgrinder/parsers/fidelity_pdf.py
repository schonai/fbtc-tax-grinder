from __future__ import annotations

import re
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

import pdfplumber
import requests

from fbtc_taxgrinder.models import MonthProceeds, YearProceeds


def parse_proceeds_line(line: str) -> dict | None:
    """Parse a single line from the Fidelity Gross Proceeds PDF text.

    Returns dict with date, btc_per_share, and optionally btc_sold_per_share
    and proceeds_per_share_usd. Returns None for non-data lines.
    """
    line = line.strip()
    if not line:
        return None

    # Fix spurious spaces in decimals: "0 .01070327" -> "0.01070327"
    line = re.sub(r"(\d)\s+\.", r"\1.", line)

    # Match: date btc_per_share [btc_sold proceeds]
    # Date format: M/D/YYYY
    match = re.match(
        r"^(\d{1,2}/\d{1,2}/\d{4})\s+"
        r"(\d+\.\d+)"
        r"(?:\s+(\d+\.\d+)\s+(\d+\.\d+))?$",
        line,
    )
    if not match:
        return None

    try:
        parts = match.group(1).split("/")
        d = date(int(parts[2]), int(parts[0]), int(parts[1]))
        btc_per_share = Decimal(match.group(2))
    except (ValueError, InvalidOperation):
        return None

    result: dict = {
        "date": d,
        "btc_per_share": btc_per_share,
        "btc_sold_per_share": None,
        "proceeds_per_share_usd": None,
    }

    if match.group(3) and match.group(4):
        result["btc_sold_per_share"] = Decimal(match.group(3))
        result["proceeds_per_share_usd"] = Decimal(match.group(4))

    return result


def parse_fidelity_pdf(source: str) -> YearProceeds:
    """Parse a Fidelity WHFIT PDF from URL or local file path.

    Args:
        source: URL (http/https) or local file path.

    Returns:
        YearProceeds with daily and monthly data.
    """
    if source.startswith("http://") or source.startswith("https://"):
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            resp = requests.get(source, timeout=30)
            resp.raise_for_status()
            tmp.write(resp.content)
            tmp.close()
            pdf_path = tmp.name
        except Exception:
            Path(tmp.name).unlink(missing_ok=True)
            raise
    else:
        pdf_path = source

    try:
        daily: dict[date, Decimal] = {}
        monthly: dict[date, MonthProceeds] = {}

        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                for line in text.split("\n"):
                    parsed = parse_proceeds_line(line)
                    if parsed is None:
                        continue
                    daily[parsed["date"]] = parsed["btc_per_share"]
                    if parsed["btc_sold_per_share"] is not None:
                        monthly[parsed["date"]] = MonthProceeds(
                            btc_sold_per_share=parsed["btc_sold_per_share"],
                            proceeds_per_share_usd=parsed["proceeds_per_share_usd"],
                        )
    finally:
        if source.startswith("http"):
            Path(pdf_path).unlink(missing_ok=True)

    source_name = source.split("/")[-1] if "/" in source else source
    return YearProceeds(daily=daily, monthly=monthly, source=source_name)

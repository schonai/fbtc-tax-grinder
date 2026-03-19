from __future__ import annotations

import re
import tempfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING

import pdfplumber
import requests

if TYPE_CHECKING:
    from pdfplumber import PDF

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


def parse_proceeds_pdf(pdf: PDF) -> tuple[dict[date, Decimal], dict[date, MonthProceeds]]:
    """Extract daily and monthly proceeds from an opened pdfplumber PDF.

    Args:
        pdf: An opened pdfplumber PDF object.

    Returns:
        Tuple of (daily, monthly) dicts.
    """
    daily: dict[date, Decimal] = {}
    monthly: dict[date, MonthProceeds] = {}

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

    return daily, monthly


def parse_fidelity_pdf_file(file_path: str) -> YearProceeds:
    """Parse a Fidelity WHFIT PDF from a local file path.

    Args:
        file_path: Local path to the PDF.

    Returns:
        YearProceeds with daily and monthly data.
    """
    with pdfplumber.open(file_path) as pdf:
        daily, monthly = parse_proceeds_pdf(pdf)

    source_name = file_path.split("/")[-1] if "/" in file_path else file_path
    return YearProceeds(daily=daily, monthly=monthly, source=source_name)


def parse_fidelity_pdf_url(url: str) -> YearProceeds:
    """Parse a Fidelity WHFIT PDF from a URL.

    Downloads the PDF to a temp file, then delegates to parse_fidelity_pdf_file.

    Args:
        url: HTTP/HTTPS URL to the PDF.

    Returns:
        YearProceeds with daily and monthly data.
    """
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
    try:
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        tmp.write(resp.content)
        tmp.close()
        result = parse_fidelity_pdf_file(tmp.name)
        # Override source to use the URL filename
        source_name = url.split("/")[-1] if "/" in url else url
        result = YearProceeds(
            daily=result.daily, monthly=result.monthly, source=source_name,
        )
        return result
    finally:
        Path(tmp.name).unlink(missing_ok=True)

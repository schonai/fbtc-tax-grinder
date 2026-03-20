from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch
from fbtc_taxgrinder.parsers.fidelity_pdf import (
    parse_proceeds_line,
    parse_proceeds_pdf,
    parse_fidelity_pdf_file,
    parse_fidelity_pdf_url,
)


def test_parse_daily_line():
    result = parse_proceeds_line("1/11/2024 0.00087448")
    assert result is not None
    assert result.date == date(2024, 1, 11)
    assert result.btc_per_share == Decimal("0.00087448")
    assert result.btc_sold_per_share is None


def test_parse_month_end_line():
    result = parse_proceeds_line("8/31/2024 0.00087430 0.00000018 0 .01070327")
    assert result is not None
    assert result.date == date(2024, 8, 31)
    assert result.btc_per_share == Decimal("0.00087430")
    assert result.btc_sold_per_share == Decimal("0.00000018")
    assert result.proceeds_per_share_usd == Decimal("0.01070327")


def test_parse_month_end_line_no_space_in_decimal():
    """2025 PDF may not have the space issue."""
    result = parse_proceeds_line("1/31/2025 0.00087339 0.00000018 0.01806356")
    assert result is not None
    assert result.proceeds_per_share_usd == Decimal("0.01806356")


def test_parse_header_line():
    result = parse_proceeds_line(
        "Bitcoin Per Per Share Bitcoin Sold To Proceeds Per Share (USD)"
    )
    assert result is None


def test_parse_empty_line():
    result = parse_proceeds_line("")
    assert result is None


def test_parse_invalid_date():
    """Invalid date should return None via ValueError catch."""
    result = parse_proceeds_line("13/32/2024 0.00087448")
    assert result is None


def test_parse_proceeds_pdf():
    """Test the pure PDF extraction function with a mock PDF object."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "Header line\n"
        "1/11/2024 0.00087448\n"
        "8/31/2024 0.00087430 0.00000018 0.01070327\n"
        "\n"
    )
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]

    daily, monthly = parse_proceeds_pdf(mock_pdf)

    assert date(2024, 1, 11) in daily
    assert daily[date(2024, 1, 11)] == Decimal("0.00087448")
    assert date(2024, 8, 31) in monthly
    assert monthly[date(2024, 8, 31)].btc_sold_per_share == Decimal("0.00000018")


def test_parse_proceeds_pdf_empty_page():
    """Pages with no text should be skipped."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = None
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]

    daily, monthly = parse_proceeds_pdf(mock_pdf)

    assert len(daily) == 0
    assert len(monthly) == 0


def test_parse_fidelity_pdf_file():
    """Test file-based parsing with mocked pdfplumber."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "1/11/2024 0.00087448\n"
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("fbtc_taxgrinder.parsers.fidelity_pdf.pdfplumber") as mock_plumber:
        mock_plumber.open.return_value = mock_pdf
        result = parse_fidelity_pdf_file("/tmp/test.pdf")

    assert result.source == "test.pdf"
    assert date(2024, 1, 11) in result.daily


def test_parse_fidelity_pdf_url():
    """Test URL download path with mocked requests and pdfplumber."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "1/11/2024 0.00087448\n"
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)

    mock_resp = MagicMock()
    mock_resp.content = b"fake pdf content"

    with (
        patch("fbtc_taxgrinder.parsers.fidelity_pdf.requests") as mock_requests,
        patch("fbtc_taxgrinder.parsers.fidelity_pdf.pdfplumber") as mock_plumber,
        patch("fbtc_taxgrinder.parsers.fidelity_pdf.Path"),
    ):
        mock_requests.get.return_value = mock_resp
        mock_plumber.open.return_value = mock_pdf
        result = parse_fidelity_pdf_url("https://example.com/test.pdf")

    assert result.source == "test.pdf"
    assert date(2024, 1, 11) in result.daily

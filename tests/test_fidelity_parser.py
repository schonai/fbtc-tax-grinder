from decimal import Decimal
from datetime import date
from unittest.mock import patch, MagicMock
from fbtc_taxgrinder.parsers.fidelity_pdf import parse_proceeds_line, parse_fidelity_pdf


def test_parse_daily_line():
    result = parse_proceeds_line("1/11/2024 0.00087448")
    assert result is not None
    assert result["date"] == date(2024, 1, 11)
    assert result["btc_per_share"] == Decimal("0.00087448")
    assert result["btc_sold_per_share"] is None


def test_parse_month_end_line():
    result = parse_proceeds_line("8/31/2024 0.00087430 0.00000018 0 .01070327")
    assert result is not None
    assert result["date"] == date(2024, 8, 31)
    assert result["btc_per_share"] == Decimal("0.00087430")
    assert result["btc_sold_per_share"] == Decimal("0.00000018")
    assert result["proceeds_per_share_usd"] == Decimal("0.01070327")


def test_parse_month_end_line_no_space_in_decimal():
    """2025 PDF may not have the space issue."""
    result = parse_proceeds_line("1/31/2025 0.00087339 0.00000018 0.01806356")
    assert result is not None
    assert result["proceeds_per_share_usd"] == Decimal("0.01806356")


def test_parse_header_line():
    result = parse_proceeds_line("Bitcoin Per Per Share Bitcoin Sold To Proceeds Per Share (USD)")
    assert result is None


def test_parse_empty_line():
    result = parse_proceeds_line("")
    assert result is None


def test_parse_invalid_date():
    """Invalid date should return None via ValueError catch."""
    result = parse_proceeds_line("13/32/2024 0.00087448")
    assert result is None


def test_parse_fidelity_pdf_local_file():
    """Test parse_fidelity_pdf with a mocked local PDF."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = (
        "Header line\n"
        "1/11/2024 0.00087448\n"
        "8/31/2024 0.00087430 0.00000018 0.01070327\n"
        "\n"
    )
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("fbtc_taxgrinder.parsers.fidelity_pdf.pdfplumber") as mock_plumber:
        mock_plumber.open.return_value = mock_pdf
        result = parse_fidelity_pdf("/tmp/test.pdf")

    assert result.source == "test.pdf"
    assert date(2024, 1, 11) in result.daily
    assert result.daily[date(2024, 1, 11)] == Decimal("0.00087448")
    assert date(2024, 8, 31) in result.monthly
    assert result.monthly[date(2024, 8, 31)].btc_sold_per_share == Decimal("0.00000018")


def test_parse_fidelity_pdf_empty_page():
    """Pages with no text should be skipped."""
    mock_page = MagicMock()
    mock_page.extract_text.return_value = None
    mock_pdf = MagicMock()
    mock_pdf.pages = [mock_page]
    mock_pdf.__enter__ = MagicMock(return_value=mock_pdf)
    mock_pdf.__exit__ = MagicMock(return_value=False)

    with patch("fbtc_taxgrinder.parsers.fidelity_pdf.pdfplumber") as mock_plumber:
        mock_plumber.open.return_value = mock_pdf
        result = parse_fidelity_pdf("/tmp/test.pdf")

    assert len(result.daily) == 0
    assert len(result.monthly) == 0


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
        patch("fbtc_taxgrinder.parsers.fidelity_pdf.Path") as mock_path,
    ):
        mock_requests.get.return_value = mock_resp
        mock_plumber.open.return_value = mock_pdf
        result = parse_fidelity_pdf("https://example.com/test.pdf")

    assert date(2024, 1, 11) in result.daily

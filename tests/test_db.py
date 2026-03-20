from decimal import Decimal
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

from fbtc_taxgrinder.db import lots, proceeds, results, state
from fbtc_taxgrinder.db.codec import encode
from fbtc_taxgrinder.models import (
    Lot, LotEvent, LotState, MonthProceeds, ExpenseResult,
    YearProceeds, YearResult,
)


def _make_lot() -> Lot:
    return Lot(
        id="lot-1",
        purchase_date=date(2024, 1, 25),
        original_shares=Decimal("204"),
        price_per_share=Decimal("34.81"),
        total_cost=Decimal("7101.24"),
        btc_per_share_on_purchase=Decimal("0.00087448"),
        source_file="test.csv",
        events=[
            LotEvent(
                type="sell",
                date=date(2025, 12, 23),
                shares=Decimal("14"),
                price_per_share=Decimal("76.2201"),
                proceeds=Decimal("1067.08"),
                disposition_id="lot-1-sell-1",
            ),
        ],
    )


class TestLots:
    def test_save_writes_to_correct_path(self):
        mock_path = MagicMock(spec=Path)
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_path)

        lot = _make_lot()
        lots.save(data_dir, [lot])

        data_dir.__truediv__.assert_called_once_with("lots.json")
        mock_path.write_text.assert_called_once()

    def test_load_returns_empty_when_missing(self):
        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = False
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_path)

        assert lots.load(data_dir) == []

    def test_load_decodes_saved_data(self):
        lot = _make_lot()
        encoded = encode([lot])

        mock_path = MagicMock(spec=Path)
        mock_path.exists.return_value = True
        mock_path.read_text.return_value = encoded
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_path)

        loaded = lots.load(data_dir)
        assert len(loaded) == 1
        assert loaded[0].id == "lot-1"
        assert loaded[0].original_shares == Decimal("204")


class TestProceeds:
    def _make_yp(self) -> YearProceeds:
        return YearProceeds(
            daily={date(2024, 1, 11): Decimal("0.00087448")},
            monthly={
                date(2024, 8, 31): MonthProceeds(
                    btc_sold_per_share=Decimal("0.00000018"),
                    proceeds_per_share_usd=Decimal("0.01070327"),
                ),
            },
            source="test.pdf",
        )

    def test_save_writes_to_correct_path(self):
        mock_subdir = MagicMock(spec=Path)
        mock_file = MagicMock(spec=Path)
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_subdir)
        mock_subdir.__truediv__ = MagicMock(return_value=mock_file)

        proceeds.save(data_dir, 2024, self._make_yp())

        data_dir.__truediv__.assert_called_once_with("proceeds")
        mock_subdir.__truediv__.assert_called_once_with("2024.json")
        mock_file.write_text.assert_called_once()

    def test_load_returns_none_when_missing(self):
        mock_subdir = MagicMock(spec=Path)
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_subdir)
        mock_subdir.__truediv__ = MagicMock(return_value=mock_file)

        assert proceeds.load(data_dir, 2024) is None

    def test_load_decodes_saved_data(self):
        yp = self._make_yp()
        encoded = encode(yp)

        mock_subdir = MagicMock(spec=Path)
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = encoded
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_subdir)
        mock_subdir.__truediv__ = MagicMock(return_value=mock_file)

        loaded = proceeds.load(data_dir, 2024)
        assert loaded is not None
        assert loaded.daily[date(2024, 1, 11)] == Decimal("0.00087448")


class TestState:
    def _make_states(self) -> dict[str, LotState]:
        return {
            "lot-1": LotState(
                adj_btc=Decimal("0.17821032"),
                adj_basis=Decimal("7093.928514"),
                shares=Decimal("204"),
            ),
        }

    def test_load_returns_none_when_missing(self):
        mock_subdir = MagicMock(spec=Path)
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_subdir)
        mock_subdir.__truediv__ = MagicMock(return_value=mock_file)

        assert state.load(data_dir, 2024) is None

    def test_load_decodes_saved_data(self):
        states = self._make_states()
        encoded = encode(states)

        mock_subdir = MagicMock(spec=Path)
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = encoded
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_subdir)
        mock_subdir.__truediv__ = MagicMock(return_value=mock_file)

        loaded = state.load(data_dir, 2024)
        assert loaded is not None
        assert loaded["lot-1"].adj_btc == Decimal("0.17821032")


class TestResults:
    def _make_yr(self) -> YearResult:
        return YearResult(
            year=2024,
            lot_results={
                "lot-1": [
                    ExpenseResult(
                        sell_date=date(2024, 8, 31), days_held=Decimal("31"), days_in_month=Decimal("31"),
                        shares=Decimal("204"), total_btc_sold=Decimal("0.00003672"),
                        cost_basis_of_sold=Decimal("1.461695179"),
                        total_expense=Decimal("2.18346708"),
                        gain_loss=Decimal("0.7217719012"),
                        adj_btc=Decimal("0.17835720"),
                        adj_basis=Decimal("7099.778305"),
                    ),
                ],
            },
            dispositions=[],
            end_states={},
            total_investment_expense=Decimal("2.18346708"),
            total_reportable_gain=Decimal("0.7217719012"),
            total_cost_basis_of_expense=Decimal("1.461695179"),
        )

    def test_load_returns_none_when_missing(self):
        mock_subdir = MagicMock(spec=Path)
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = False
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_subdir)
        mock_subdir.__truediv__ = MagicMock(return_value=mock_file)

        assert results.load(data_dir, 2024) is None

    def test_load_decodes_saved_data(self):
        yr = self._make_yr()
        encoded = encode(yr)

        mock_subdir = MagicMock(spec=Path)
        mock_file = MagicMock(spec=Path)
        mock_file.exists.return_value = True
        mock_file.read_text.return_value = encoded
        data_dir = MagicMock(spec=Path)
        data_dir.__truediv__ = MagicMock(return_value=mock_subdir)
        mock_subdir.__truediv__ = MagicMock(return_value=mock_file)

        loaded = results.load(data_dir, 2024)
        assert loaded is not None
        assert loaded.year == 2024
        assert loaded.lot_results["lot-1"][0].adj_btc == Decimal("0.17835720")

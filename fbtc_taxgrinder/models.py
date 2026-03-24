"""Core domain dataclasses for FBTC tax lot computation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum


@dataclass
class LotEvent:
    """A sell event recorded against a lot."""

    type: str  # "sell"
    date: date
    shares: Decimal
    price_per_share: Decimal
    proceeds: Decimal
    disposition_id: str


@dataclass
class Lot:
    """A purchased tax lot with its trade history."""

    id: str
    purchase_date: date
    original_shares: Decimal
    price_per_share: Decimal
    total_cost: Decimal
    btc_per_share_on_purchase: Decimal
    source_file: str
    events: list[LotEvent] = field(default_factory=list)

    def shares_at_date(self, d: date) -> Decimal:
        """Return share count at a given date (sells reduce on their date)."""
        shares = self.original_shares
        for event in self.events:
            if event.type == "sell" and event.date <= d:
                shares -= event.shares
        return shares


@dataclass
class LotState:
    """Year-end snapshot of a lot's adjusted values."""

    adj_btc: Decimal
    adj_basis: Decimal
    shares: Decimal


@dataclass
class MonthProceeds:
    """Monthly BTC sold and USD proceeds per share from Fidelity PDF."""

    btc_sold_per_share: Decimal
    proceeds_per_share_usd: Decimal


@dataclass
class YearProceeds:
    """Full year of daily and monthly proceeds data from a Fidelity PDF."""

    daily: dict[date, Decimal]  # date -> btc_per_share
    monthly: dict[date, MonthProceeds]  # month_end_date -> MonthProceeds
    source: str


class HoldingTerm(Enum):
    """IRS holding period classification for WHFIT expense gain/loss."""

    LONG_TERM = "long_term"
    SHORT_TERM = "short_term"


@dataclass
class ExpenseResult:
    """Result of the 6-step expense calculation for one lot-month."""

    sell_date: date
    days_held: Decimal
    days_in_month: Decimal
    shares: Decimal
    total_btc_sold: Decimal
    cost_basis_of_sold: Decimal
    total_expense: Decimal
    gain_loss: Decimal
    adj_btc: Decimal
    adj_basis: Decimal
    holding_term: HoldingTerm


@dataclass
class Disposition:
    """A share disposition (sale) with proceeds and gain/loss."""

    lot_id: str
    disposition_id: str
    date_sold: date
    shares_sold: Decimal
    proceeds: Decimal
    disposed_btc: Decimal
    disposed_basis: Decimal
    gain_loss: Decimal


@dataclass
class YearResult:
    """Aggregated computation results for an entire tax year."""

    year: int
    lot_results: dict[str, list[ExpenseResult]]  # lot_id -> per-sell-date results
    dispositions: list[Disposition]
    end_states: dict[str, LotState]  # lot_id -> year-end state
    total_investment_expense: Decimal
    total_reportable_gain: Decimal
    total_cost_basis_of_expense: Decimal

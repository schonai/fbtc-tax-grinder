from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal


@dataclass
class LotEvent:
    type: str  # "sell"
    date: date
    shares: Decimal
    price_per_share: Decimal
    proceeds: Decimal
    disposition_id: str


@dataclass
class Lot:
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
    adj_btc: Decimal
    adj_basis: Decimal
    shares: Decimal


@dataclass
class MonthProceeds:
    btc_sold_per_share: Decimal
    proceeds_per_share_usd: Decimal


@dataclass
class YearProceeds:
    daily: dict[date, Decimal]  # date -> btc_per_share
    monthly: dict[date, MonthProceeds]  # month_end_date -> MonthProceeds
    source: str


@dataclass
class MonthResult:
    month: int
    days_held: Decimal
    days_in_month: Decimal
    shares: Decimal
    total_btc_sold: Decimal
    cost_basis_of_sold: Decimal
    total_expense: Decimal
    gain_loss: Decimal
    adj_btc: Decimal
    adj_basis: Decimal


@dataclass
class Disposition:
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
    year: int
    lot_results: dict[str, list[MonthResult]]  # lot_id -> monthly results
    dispositions: list[Disposition]
    end_states: dict[str, LotState]  # lot_id -> year-end state
    total_investment_expense: Decimal
    total_reportable_gain: Decimal
    total_cost_basis_of_expense: Decimal

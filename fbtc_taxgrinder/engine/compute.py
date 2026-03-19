from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass
class PeriodResult:
    total_btc_sold: Decimal
    cost_basis_of_sold: Decimal
    total_expense: Decimal
    gain_loss: Decimal
    adj_btc: Decimal
    adj_basis: Decimal


def compute_period(
    *,
    days_held: Decimal,
    days_in_month: Decimal,
    shares: Decimal,
    adj_btc: Decimal,
    adj_basis: Decimal,
    original_total_cost: Decimal,
    monthly_btc_sold_per_share: Decimal,
    monthly_proceeds_per_share_usd: Decimal,
) -> PeriodResult:
    """Run Steps 1-6 for a single contiguous period within a month."""
    if days_held == 0 or shares == 0:
        return PeriodResult(
            total_btc_sold=Decimal("0"),
            cost_basis_of_sold=Decimal("0"),
            total_expense=Decimal("0"),
            gain_loss=Decimal("0"),
            adj_btc=adj_btc,
            adj_basis=adj_basis,
        )

    proration = days_held / days_in_month

    # Step 2
    total_btc_sold = Decimal("0")
    cost_basis_of_sold = Decimal("0")
    if monthly_btc_sold_per_share != 0:
        btc_sold_per_share = proration * monthly_btc_sold_per_share
        total_btc_sold = btc_sold_per_share * shares
        # Step 3
        cost_basis_of_sold = (total_btc_sold / adj_btc) * original_total_cost

    # Step 4
    expense_per_share = proration * monthly_proceeds_per_share_usd
    total_expense = expense_per_share * shares

    # Step 5
    gain_loss = total_expense - cost_basis_of_sold

    # Step 6
    new_adj_btc = adj_btc - total_btc_sold
    new_adj_basis = adj_basis - cost_basis_of_sold

    return PeriodResult(
        total_btc_sold=total_btc_sold,
        cost_basis_of_sold=cost_basis_of_sold,
        total_expense=total_expense,
        gain_loss=gain_loss,
        adj_btc=new_adj_btc,
        adj_basis=new_adj_basis,
    )

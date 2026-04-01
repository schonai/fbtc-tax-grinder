"""CLI commands for FBTC Tax Grinder."""

from __future__ import annotations

from pathlib import Path

import click

from fbtc_taxgrinder.db import lots as lots_db
from fbtc_taxgrinder.db import proceeds as proceeds_db
from fbtc_taxgrinder.db import results as results_db
from fbtc_taxgrinder.db import state as state_db
from fbtc_taxgrinder.engine.compute import HoldingMode, compute_year
from fbtc_taxgrinder.engine.matching import match_sell_to_lot
from fbtc_taxgrinder.export.csv_export import export_year_csv
from fbtc_taxgrinder.models import Lot, LotEvent
from fbtc_taxgrinder.parsers.etrade import parse_etrade_csv
from fbtc_taxgrinder.parsers.fidelity_pdf import (
    parse_fidelity_pdf_file,
    parse_fidelity_pdf_url,
)


def _project_dir(ctx: click.Context) -> Path:
    return ctx.obj["project_dir"]


def _int_stems(directory: Path) -> list[int]:
    """Extract integer stems from .json files, skipping non-numeric names."""
    results = []
    for f in directory.glob("*.json"):
        try:
            results.append(int(f.stem))
        except ValueError:
            continue
    return results


@click.group()
@click.option(
    "--project",
    "project_dir",
    type=click.Path(path_type=Path),
    required=True,
    help="Path to project directory.",
)
@click.pass_context
def cli(ctx: click.Context, project_dir: Path) -> None:
    """FBTC Tax Lot Grinder — compute IRS-reportable WHFIT tax lots."""
    ctx.ensure_object(dict)
    ctx.obj["project_dir"] = project_dir
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "proceeds").mkdir(exist_ok=True)
    (project_dir / "results").mkdir(exist_ok=True)
    (project_dir / "state").mkdir(exist_ok=True)
    (project_dir / "output").mkdir(exist_ok=True)


@cli.command("import-proceeds")
@click.option("--url", help="URL to Fidelity WHFIT PDF.")
@click.option("--file", "file_path", help="Local path to Fidelity WHFIT PDF.")
@click.pass_context
def import_proceeds(ctx: click.Context, url: str | None, file_path: str | None) -> None:
    """Import Fidelity Gross Proceeds data from PDF."""
    if not url and not file_path:
        raise click.UsageError("Provide --url or --file.")

    if file_path and not Path(file_path).exists():
        raise click.ClickException(f"File not found: {file_path}")

    if url:
        click.echo(f"Parsing proceeds from {url}...")
        yp = parse_fidelity_pdf_url(url)
    else:
        assert file_path is not None
        click.echo(f"Parsing proceeds from {file_path}...")
        yp = parse_fidelity_pdf_file(file_path)

    # Detect year from data
    if not yp.daily:
        raise click.ClickException("No data found in PDF.")
    first_date = min(yp.daily.keys())
    year = first_date.year

    dd = _project_dir(ctx)
    existing = proceeds_db.load(dd, year)
    if existing is not None:
        click.echo(
            f"Proceeds for {year} already imported ({existing.source}). Skipping."
        )
        return

    proceeds_db.save(dd, year, yp)
    click.echo(
        f"Imported {year} proceeds: {len(yp.daily)} daily rows, "
        f"{len(yp.monthly)} month-end rows."
    )


@cli.command("import-trades")
@click.option("--file", "file_path", required=True, help="Path to ETrade CSV file.")
@click.pass_context
def import_trades(ctx: click.Context, file_path: str) -> None:
    """Import FBTC trades (buys and sells) from ETrade CSV."""
    if not Path(file_path).exists():
        raise click.ClickException(f"File not found: {file_path}")

    dd = _project_dir(ctx)
    parsed = parse_etrade_csv(file_path)
    existing_lots = lots_db.load(dd)

    # Track existing lots by (date, shares, price) for idempotency
    existing_keys = {
        (lot.purchase_date, lot.original_shares, lot.price_per_share)
        for lot in existing_lots
    }

    next_id = len(existing_lots) + 1
    new_lots = 0
    source_name = Path(file_path).resolve().as_uri()

    for buy in parsed.buys:
        key = (buy.date, buy.shares, buy.price_per_share)
        if key in existing_keys:
            continue

        # Look up btc_per_share on purchase date
        year = buy.date.year
        yp = proceeds_db.load(dd, year)
        if yp is None:
            raise click.ClickException(
                f"Proceeds for {year} not imported. " f"Run 'import-proceeds' first."
            )
        btc = yp.daily.get(buy.date)
        if btc is None:
            raise click.ClickException(
                f"No BTC-per-share data for {buy.date.isoformat()} in {year} proceeds."
            )

        lot = Lot(
            id=f"lot-{next_id}",
            purchase_date=buy.date,
            original_shares=buy.shares,
            price_per_share=buy.price_per_share,
            total_cost=buy.total_cost,
            btc_per_share_on_purchase=btc,
            source_file=source_name,
            events=[],
        )
        existing_lots.append(lot)
        existing_keys.add(key)
        next_id += 1
        new_lots += 1

    # Process sells
    new_sells = 0
    for sell in parsed.sells:
        try:
            matched_lot = match_sell_to_lot(
                existing_lots,
                sell_shares=sell.shares,
                sell_date=sell.date,
            )
        except ValueError as e:
            raise click.ClickException(str(e))
        # Check idempotency: skip if this sell already recorded
        already_exists = any(
            e.date == sell.date
            and e.shares == sell.shares
            and e.price_per_share == sell.price_per_share
            for e in matched_lot.events
        )
        if already_exists:
            continue

        sell_count = sum(1 for e in matched_lot.events if e.type == "sell")
        matched_lot.events.append(
            LotEvent(
                type="sell",
                date=sell.date,
                shares=sell.shares,
                price_per_share=sell.price_per_share,
                proceeds=sell.proceeds,
                disposition_id=f"{matched_lot.id}-sell-{sell_count + 1}",
            )
        )
        new_sells += 1

    lots_db.save(dd, existing_lots)
    click.echo(f"Imported {new_lots} new lots, {new_sells} new sells.")


@cli.command()
@click.option("--year", required=True, type=int, help="Tax year to compute.")
@click.option("--force", is_flag=True, help="Recompute even if results exist.")
@click.option(
    "--full-month",
    is_flag=True,
    default=False,
    help="Use full-month granularity for buy and sell months. "
    "This is the default and matches Fidelity's 1099 calculations.",
)
@click.option(
    "--prorate",
    is_flag=True,
    default=False,
    help="Prorate buy and sell months by actual days held. "
    "This matches Fidelity's WHFIT document example "
    "but produces values that differ from the 1099.",
)
@click.pass_context
def compute(
    ctx: click.Context, year: int, force: bool, full_month: bool, prorate: bool
) -> None:
    """Compute tax lots for a given year."""
    if full_month and prorate:
        raise click.UsageError("--full-month and --prorate are mutually exclusive.")
    holding_mode = HoldingMode.PRORATE if prorate else HoldingMode.FULL_MONTH

    dd = _project_dir(ctx)

    # Check for existing results
    if not force and results_db.load(dd, year) is not None:
        click.echo(f"Results for {year} already computed. Use --force to recompute.")
        return

    # Load proceeds
    yp = proceeds_db.load(dd, year)
    if yp is None:
        raise click.ClickException(
            f"No proceeds data for {year}. Run 'import-proceeds' first."
        )

    # Load lots
    all_lots = lots_db.load(dd)
    if not all_lots:
        raise click.ClickException("No lots found. Run 'import-trades' first.")

    # Load prior state chain
    prior = None
    if year > min(lot.purchase_date.year for lot in all_lots):
        prior = state_db.load(dd, year - 1)

    try:
        result = compute_year(
            lots=all_lots,
            proceeds=yp,
            prior_state=prior,
            year=year,
            holding_mode=holding_mode,
        )
    except ValueError as e:
        raise click.ClickException(str(e))

    # Save results and year-end state
    results_db.save(dd, result)
    state_db.save(dd, year, result.end_states)

    click.echo(
        f"Computed {year}: "
        f"expense=${result.total_investment_expense:.2f}, "
        f"gain=${result.total_reportable_gain:.2f}, "
        f"dispositions={len(result.dispositions)}"
    )


@cli.command()
@click.option("--year", required=True, type=int)
@click.pass_context
def export(ctx: click.Context, year: int) -> None:
    """Export computed results."""
    dd = _project_dir(ctx)
    yr = results_db.load(dd, year)
    if yr is None:
        raise click.ClickException(f"No results for {year}. Run 'compute' first.")
    output_dir = dd / "output"
    export_year_csv(yr, output_dir)
    click.echo(f"Exported {year} results to {output_dir}/")


@cli.command("lots")
@click.pass_context
def list_lots(ctx: click.Context) -> None:
    """List all lots and their events."""
    dd = _project_dir(ctx)
    all_lots = lots_db.load(dd)
    if not all_lots:
        click.echo("No lots found.")
        return
    for lot in all_lots:
        click.echo(
            f"{lot.id}: {lot.purchase_date} | {lot.original_shares} shares "
            f"@ ${lot.price_per_share} | cost=${lot.total_cost}"
        )
        for e in lot.events:
            click.echo(
                f"  {e.type}: {e.date} | {e.shares} shares "
                f"@ ${e.price_per_share} | proceeds=${e.proceeds}"
            )


@cli.command()
@click.pass_context
def status(ctx: click.Context) -> None:
    """Show what data is imported and computed."""
    dd = _project_dir(ctx)
    all_lots = lots_db.load(dd)
    click.echo(f"Lots: {len(all_lots)} lots")
    sells = sum(len(lot.events) for lot in all_lots)
    click.echo(f"Sell events: {sells}")

    # Check proceeds years
    proceeds_dir = dd / "proceeds"
    if proceeds_dir.exists():
        years = sorted(_int_stems(proceeds_dir))
        click.echo(f"Proceeds: {', '.join(str(y) for y in years) if years else 'none'}")
    else:
        click.echo("Proceeds: none")

    # Check computed years
    results_dir = dd / "results"
    if results_dir.exists():
        years = sorted(_int_stems(results_dir))
        click.echo(f"Computed: {', '.join(str(y) for y in years) if years else 'none'}")
    else:
        click.echo("Computed: none")

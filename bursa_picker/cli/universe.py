from __future__ import annotations

from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from bursa_picker.data.universe import filter_universe, load_ticker_map

app = typer.Typer(help="Inspect the tradable universe after liquidity filters.")


def _parse_money(v: str) -> float:
    v = v.strip().lower()
    mult = 1.0
    if v.endswith("m"):
        mult = 1e6
        v = v[:-1]
    elif v.endswith("k"):
        mult = 1e3
        v = v[:-1]
    elif v.endswith("b"):
        mult = 1e9
        v = v[:-1]
    return float(v) * mult


@app.callback(invoke_without_command=True)
def universe(
    as_of: str = typer.Option("today", "--as-of", help="YYYY-MM-DD or 'today'"),
    min_mcap: Optional[str] = typer.Option(None, help="Minimum market cap (e.g. 100m, 1b)"),
    min_adv: Optional[str] = typer.Option(None, help="Minimum 30-day ADV (e.g. 500k)"),
    min_price: Optional[float] = typer.Option(None, help="Minimum last close in MYR"),
    output: str = typer.Option("table", help="table|csv"),
    refresh: bool = typer.Option(False, "--refresh", help="Force cache bust"),
) -> None:
    """Print the filtered tradable universe."""
    mapping = load_ticker_map()
    df = filter_universe(
        mapping,
        as_of=None if as_of == "today" else as_of,
        min_mcap_myr=_parse_money(min_mcap) if min_mcap else None,
        min_adv_myr=_parse_money(min_adv) if min_adv else None,
        min_price_myr=min_price,
        refresh=refresh,
    )

    if output == "csv":
        typer.echo(df.reset_index().to_csv(index=False))
        return

    console = Console()
    tbl = Table(title=f"Tradable universe ({len(df)} tickers)")
    tbl.add_column("Ticker")
    tbl.add_column("Code")
    tbl.add_column("Sector")
    tbl.add_column("MktCap(MYR m)", justify="right")
    tbl.add_column("LastClose(MYR)", justify="right")
    tbl.add_column("ADV30(MYR k)", justify="right")
    for ticker, row in df.head(50).iterrows():
        tbl.add_row(
            ticker,
            str(row.stock_code),
            str(row.sector),
            f"{row.mcap/1e6:,.0f}" if row.mcap == row.mcap else "-",
            f"{row.last_close:.2f}" if row.last_close == row.last_close else "-",
            f"{row.adv30/1e3:,.0f}" if row.adv30 == row.adv30 else "-",
        )
    console.print(tbl)
    if len(df) > 50:
        console.print(f"[dim]... {len(df) - 50} more rows. Use --output csv for full list.[/dim]")

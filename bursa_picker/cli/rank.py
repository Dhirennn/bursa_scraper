from __future__ import annotations

import json
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from bursa_picker.portfolio.construction import rank_universe

app = typer.Typer(help="Rank Bursa tickers by the 6-factor composite score.")


@app.callback(invoke_without_command=True)
def rank(
    top: int = typer.Option(20, "--top", help="Number of picks to output"),
    date: str = typer.Option("today", "--date", help="YYYY-MM-DD or 'today'"),
    narrative: bool = typer.Option(False, "--narrative", help="Print plain-English paragraphs"),
    factors: Optional[str] = typer.Option(
        None,
        "--factors",
        help="Comma-separated subset to enable (e.g. 'quality,value,dividend'). Default: all six.",
    ),
    sector_cap: Optional[float] = typer.Option(
        None, "--sector-cap", help="Max share per sector in the top-N (e.g. 0.30)"
    ),
    output: str = typer.Option("table", help="table|json"),
    refresh: bool = typer.Option(False, "--refresh", help="Force cache bust"),
) -> None:
    """Rank the filtered universe by the 6-factor composite score."""
    weights_override = None
    if factors:
        allowed = {f.strip() for f in factors.split(",") if f.strip()}
        unknown = allowed - {"quality", "value", "dividend", "momentum", "size", "sentiment"}
        if unknown:
            raise typer.BadParameter(f"Unknown factors: {sorted(unknown)}")
        weights_override = {k: 1.0 for k in allowed}

    result = rank_universe(
        as_of=None if date == "today" else date,
        top_n=top,
        weights=weights_override,
        refresh=refresh,
        sector_cap=sector_cap,
    )

    if output == "json":
        payload = {
            "as_of": result.as_of.strftime("%Y-%m-%d"),
            "universe_stats": result.universe_stats,
            "warnings": result.warnings,
            "picks": [
                {
                    "rank": int(row["rank"]),
                    "ticker": ticker,
                    "stock_code": row["stock_code"],
                    "sector": row["sector"],
                    "score": float(row["score"]),
                    "mcap_myr": float(row["mcap"]),
                    "last_close": float(row["last_close"]),
                    "contributions": {
                        f: float(result.contributions.loc[ticker, f])
                        for f in result.contributions.columns
                        if f != "_n_missing"
                    },
                }
                for ticker, row in result.picks.iterrows()
            ],
        }
        typer.echo(json.dumps(payload, indent=2))
        return

    console = Console()
    tbl = Table(
        title=f"Top {len(result.picks)} Bursa picks · {result.as_of.strftime('%Y-%m-%d')} · "
        f"universe {result.universe_stats['universe_size']}"
    )
    tbl.add_column("#", justify="right")
    tbl.add_column("Ticker")
    tbl.add_column("Code")
    tbl.add_column("Sector")
    tbl.add_column("Score", justify="right")
    tbl.add_column("MktCap (MYR m)", justify="right")
    tbl.add_column("Last", justify="right")
    tbl.add_column("Q", justify="right")
    tbl.add_column("V", justify="right")
    tbl.add_column("D", justify="right")
    tbl.add_column("M", justify="right")
    tbl.add_column("S", justify="right")
    tbl.add_column("A", justify="right")

    for ticker, row in result.picks.iterrows():
        c = result.contributions.loc[ticker]
        tbl.add_row(
            str(int(row["rank"])),
            ticker,
            str(row["stock_code"]),
            str(row["sector"])[:18],
            f"{row['score']:+.2f}",
            f"{row['mcap'] / 1e6:,.0f}",
            f"{row['last_close']:.2f}",
            f"{c['quality']:+.2f}",
            f"{c['value']:+.2f}",
            f"{c['dividend']:+.2f}",
            f"{c['momentum']:+.2f}",
            f"{c['size']:+.2f}",
            f"{c['sentiment']:+.2f}",
        )

    console.print(tbl)
    for w in result.warnings:
        console.print(f"[yellow]⚠ {w}[/yellow]")

    if narrative:
        from bursa_picker.explain.narrative import (
            DISCLAIMER,
            citations_footer,
            render_pick,
        )

        console.print()
        for ticker, row in result.picks.iterrows():
            c = result.contributions.loc[ticker]
            fund = result.fundamentals.loc[ticker]
            para = render_pick(
                ticker,
                row,
                c,
                fund,
                rank=int(row["rank"]),
                total=len(result.picks),
            )
            console.print(para)
            console.print()

        console.print("[bold]Why this factor mix:[/bold]")
        console.print(citations_footer(["quality", "value", "dividend", "momentum", "size", "sentiment"]))
        console.print()
        console.print(
            "[italic dim]"
            + DISCLAIMER.format(date=result.as_of.strftime("%Y-%m-%d"))
            + "[/italic dim]"
        )

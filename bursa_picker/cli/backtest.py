from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from bursa_picker.backtest.runner import run_from_config
from bursa_picker.config import get_settings

app = typer.Typer(help="Walk-forward backtest (price-only factors).")


@app.callback(invoke_without_command=True)
def backtest(
    start: str = typer.Option(None, "--start", help="YYYY-MM-DD (default: config)"),
    end: str = typer.Option("today", "--end", help="YYYY-MM-DD or 'today'"),
    top: int = typer.Option(20, "--top", help="Top-N picks per rebalance"),
    costs: Optional[float] = typer.Option(None, help="Roundtrip costs in basis points"),
    min_fee: Optional[float] = typer.Option(None, help="Per-trade MYR floor"),
    output: str = typer.Option("table", help="table|json"),
    save_json: Optional[str] = typer.Option(None, help="Save picks log to this JSON file"),
    refresh: bool = typer.Option(False, "--refresh", help="Force cache bust"),
) -> None:
    """Run the price-only walk-forward backtest over the filtered universe."""
    settings = get_settings()
    start = start or settings.backtest.start
    import pandas as pd
    end_str = (
        pd.Timestamp.today().strftime("%Y-%m-%d") if end == "today" else end
    )

    result = run_from_config(
        start=start,
        end=end_str,
        top_n=top,
        costs_bps=costs,
        min_fee_myr=min_fee,
        refresh=refresh,
    )

    console = Console()

    if output == "json":
        typer.echo(
            json.dumps(
                {
                    "report": {k: (float(v) if isinstance(v, (int, float)) else v) for k, v in result.report.items()},
                    "picks_log": {
                        str(ts.date()): tickers for ts, tickers in result.picks_log.items()
                    },
                },
                indent=2,
            )
        )
        return

    tbl = Table(title=f"Backtest · {result.report['start']} → {result.report['end']} · price-only factors")
    tbl.add_column("Metric")
    tbl.add_column("Value", justify="right")
    for k in ("CAGR", "Bench_CAGR", "ExcessCAGR", "Sharpe", "MaxDD", "HitRate", "Turnover_avg"):
        v = result.report.get(k)
        if isinstance(v, float):
            if k in ("CAGR", "Bench_CAGR", "ExcessCAGR", "MaxDD"):
                cell = f"{v * 100:+.2f}%"
            elif k == "HitRate":
                cell = f"{v * 100:.1f}%"
            elif k == "Turnover_avg":
                cell = f"{v * 100:.1f}%"
            else:
                cell = f"{v:.2f}"
        else:
            cell = str(v)
        tbl.add_row(k, cell)
    tbl.add_row("NAV final (MYR)", f"{result.report['NAV_final']:,.0f}")
    tbl.add_row("Rebalances", str(result.report["N_rebalances"]))
    console.print(tbl)

    console.print(
        "[italic dim]Note: this backtest is price-only. "
        "Fundamentals point-in-time are not available from yfinance for KLSE, "
        "so the live ranker's fundamentals overlay is literature-supported but "
        "not Bursa-walk-forward-validated.[/italic dim]"
    )

    if save_json:
        out = Path(save_json)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(
            json.dumps(
                {
                    "report": result.report,
                    "picks_log": {
                        str(ts.date()): tickers for ts, tickers in result.picks_log.items()
                    },
                    "nav": {str(ts.date()): float(v) for ts, v in result.nav.items()},
                },
                indent=2,
                default=str,
            )
        )
        console.print(f"[dim]Saved full picks log + NAV → {out}[/dim]")

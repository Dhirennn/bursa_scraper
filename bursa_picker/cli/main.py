from __future__ import annotations

import typer

from bursa_picker import __version__

app = typer.Typer(
    name="bursa-picker",
    help="Research-backed factor picker for Bursa Malaysia equities.",
    no_args_is_help=True,
    add_completion=False,
)


@app.callback()
def _root(
    config: str = typer.Option(None, "--config", help="Path to config.toml"),
    log_level: str = typer.Option("INFO", "--log-level", help="DEBUG|INFO|WARN|ERROR"),
    json_output: bool = typer.Option(False, "--json", help="Machine-readable JSON"),
) -> None:
    """Global flags."""
    # Config/logging wiring lands in checkpoint 2.
    return


@app.command()
def version() -> None:
    """Print version."""
    typer.echo(__version__)


from bursa_picker.cli import rank as _rank
from bursa_picker.cli import universe as _universe

app.add_typer(_universe.app, name="universe")
app.add_typer(_rank.app, name="rank")

# Subcommands registered in later checkpoints:
#   backtest  → bursa_picker.cli.backtest


if __name__ == "__main__":
    app()

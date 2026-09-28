"""The `pmcc` command line. Each command is a stub until its backlog item lands."""

from datetime import datetime
from pathlib import Path
from typing import Annotated, NoReturn

import typer

from pmcc.config.calendar import load_calendar
from pmcc.data.lseg import lseg_session
from pmcc.data.probe import ProbeStoppedError, probe_path, run_probe, write_report
from pmcc.data.provider import ProviderOutageError
from pmcc.domain.clock import ET
from pmcc.log import configure_logging

app = typer.Typer(help="PMCC backtester: fetch LSEG data, run backtests, export the site.")


def _now() -> datetime:
    return datetime.now(ET)


Symbol = Annotated[str, typer.Option(help="Underlying ticker, e.g. NVDA.")]
Day = Annotated[datetime, typer.Option(formats=["%Y-%m-%d"])]
Universe = Annotated[Path, typer.Option(help="Universe YAML.")]


def _not_built(item: str) -> NoReturn:
    typer.echo(f"Not built yet: see docs/BUILD-PLAN.md {item}.", err=True)
    raise typer.Exit(code=1)


@app.command()
def fetch(
    symbol: Symbol,
    start: Day,
    end: Day,
    plan_only: Annotated[bool, typer.Option(help="Print the request estimate and stop.")] = False,
) -> None:
    """Pull a symbol's stock and option history from LSEG into the local cache."""
    _not_built("P1-08")


@app.command()
def probe(
    symbol: Symbol,
    out: Annotated[Path, typer.Option(help="Where probe reports go.")] = Path("data_cache/probes"),
) -> None:
    """Run the LSEG spikes for a symbol and write a probe report."""
    configure_logging("probe")
    sym, now = symbol.upper(), _now()
    path = probe_path(out, sym, now.date())
    if path.exists():
        _fail(f"{path} exists; a probe report is never overwritten. Rename it to probe again.")
    try:
        with lseg_session() as provider:
            report = run_probe(provider, sym, load_calendar(), now)
    except (ProviderOutageError, ProbeStoppedError) as exc:
        _fail(f"{sym}: the probe stopped and wrote nothing: {exc}")
    write_report(report, path)
    typer.echo(f"{sym}: {report['requests']} requests; report written to {path}")
    if report["stopped"] is not None:
        _fail(f"{sym}: stopped early: {report['stopped']}")


def _fail(message: str) -> NoReturn:
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


@app.command()
def run(
    symbol: Symbol,
    config: Annotated[Path, typer.Option(help="Strategy config YAML.")],
) -> None:
    """Backtest one strategy config on one symbol, from the cache only."""
    _not_built("P3-08")


@app.command()
def batch(universe: Universe = Path("configs/universe.yaml")) -> None:
    """Run every symbol, strategy and variant in the universe."""
    _not_built("P5-03")


@app.command()
def calibrate(universe: Universe = Path("configs/universe.yaml")) -> None:
    """Calibrate starting capital across the universe."""
    _not_built("P3-09")


@app.command()
def export(
    out: Annotated[Path, typer.Option(help="Site data directory.")] = Path("web/public/data"),
) -> None:
    """Write site data and JSON Schema from committed results."""
    _not_built("P4-05")


@app.command()
def verify(results: Annotated[Path, typer.Argument()] = Path("results")) -> None:
    """Re-derive invariants from results and reject any that fail."""
    _not_built("P4-05")


@app.command()
def serve() -> None:
    """Serve the built site and the local data endpoints on 127.0.0.1."""
    _not_built("P7-06")

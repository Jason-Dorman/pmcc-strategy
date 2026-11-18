"""`live.json` (L4-01; UI-SPEC §6 › Live): the live wheel's page data, from the repo root's files.

- `open_orders.json`, read through the order language's checks (the root copy: the nightly run
  writes the same file under `mkt/`, and refuses to run when the two differ, LD-04);
- Sanji's `positions.json` and `fills.json` (under `mkt/` first, then the root), their text as
  written: their format is unknown until Sanji resolves an order (L5-01), so they are published,
  never parsed, and a file he leaves half-written can't stop the site's export; null when absent;
- `live/runs.jsonl`, every row, the pick's quote included (PO, LD-15); none before the first run;
- the root's `configs/live.yaml`: its rules in their words, the conid, the starting cash and r;
- `live/vol.jsonl` and `live/smile.json`, the volatility workflow's (L4-02; PO, LD-33): the
  points by session, a session twice refused; none and null before its first run;
- the wheel's backtest on the symbol, from its committed result (Spec › Why the wheel).

Derived at export time, like `index.json`, so the page can't disagree with the files it shows.
"""

from collections.abc import Sequence
from pathlib import Path

from pydantic import ValidationError

from pmcc.export.live_models import (
    Live,
    LiveBacktest,
    LiveOrder,
    LiveRiskFree,
    LiveRuleOut,
    LiveRun,
    SanjiFileOut,
    SmileOut,
    VolPointOut,
)
from pmcc.export.wheel_models import WheelResult
from pmcc.live.book import FILLS, POSITIONS, sanji_file
from pmcc.live.config import LiveConfig
from pmcc.live.names import ORDERS
from pmcc.live.orders import OrderError, read_orders
from pmcc.live.run import RUN_LOG
from pmcc.live.vol import SMILE, VOL_LOG

LIVE = "live.json"
CONFIG = Path("configs") / "live.yaml"  # under the repo root


class LiveDataError(Exception):
    """A live file the page can't be built from: nothing is exported."""


def build_live(root: Path, config: LiveConfig, wheel: tuple[str, WheelResult] | None) -> Live:
    """The page's data from `root`, with `wheel` (its index path and result) as the backtest.
    Raises `LiveDataError` if the orders or the run log can't be read."""
    return Live(
        symbol=config.symbol,
        underlying_conid=config.underlying_conid,
        starting_cash=config.cash.to_dollars(),
        risk_free=LiveRiskFree(
            investment_yield_pct=config.risk_free.investment_yield_pct,
            observed=config.risk_free.observed.isoformat(),
            source=config.risk_free.source,
            rate=config.risk_free.rate,
        ),
        rules=tuple(LiveRuleOut(id=r.id, rule=r.rule, words=r.words()) for r in config.rules),
        orders=_orders(root / ORDERS),
        positions=_sanji(root, POSITIONS),
        fills=_sanji(root, FILLS),
        runs=_runs(root / RUN_LOG),
        backtest=None if wheel is None else _backtest(*wheel),
        vol=_vol(root / VOL_LOG),
        smile=_smile(root / SMILE),
    )


def _orders(path: Path) -> tuple[LiveOrder, ...]:
    try:
        orders = read_orders(path)
    except OrderError as exc:
        raise LiveDataError(f"{ORDERS}: {exc}") from exc
    # JSON mode writes `for` as its ISO date, as the file holds it.
    return tuple(
        LiveOrder.model_validate(order.model_dump(mode="json", by_alias=True)) for order in orders
    )


def _sanji(root: Path, name: str) -> SanjiFileOut | None:
    path = sanji_file(root, name)
    if path is None:
        return None
    where = path.relative_to(root).as_posix()
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise LiveDataError(f"{where}: {exc}") from exc
    return SanjiFileOut(path=where, text=raw.decode("utf-8", errors="replace"))


def _runs(path: Path) -> tuple[LiveRun, ...]:
    if not path.exists():
        return ()  # before the first nightly run
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise LiveDataError(f"{RUN_LOG.as_posix()}: {exc}") from exc
    return tuple(_run(n, line) for n, line in enumerate(lines, start=1) if line.strip())


def _run(n: int, line: str) -> LiveRun:
    try:
        # Lax: the log writes money as strings ("25000.00"), which the page's dollars read.
        return LiveRun.model_validate_json(line, strict=False)
    except ValidationError as exc:
        raise LiveDataError(f"{RUN_LOG.as_posix()} line {n}: {exc}") from exc


def _vol(path: Path) -> tuple[VolPointOut, ...]:
    if not path.exists():
        return ()  # before the volatility workflow's first run
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise LiveDataError(f"{VOL_LOG.as_posix()}: {exc}") from exc
    points = [_point(n, line) for n, line in enumerate(lines, start=1) if line.strip()]
    sessions = [p.session for p in points]
    twice = sorted({s for s in sessions if sessions.count(s) > 1})
    if twice:
        raise LiveDataError(f"{VOL_LOG.as_posix()}: a session twice: {', '.join(twice)}")
    return tuple(sorted(points, key=lambda p: p.session))


def _point(n: int, line: str) -> VolPointOut:
    try:
        return VolPointOut.model_validate_json(line, strict=False)  # money as strings, as logged
    except ValidationError as exc:
        raise LiveDataError(f"{VOL_LOG.as_posix()} line {n}: {exc}") from exc


def _smile(path: Path) -> SmileOut | None:
    if not path.exists():
        return None
    try:
        return SmileOut.model_validate_json(path.read_bytes(), strict=False)
    except (OSError, ValidationError) as exc:
        raise LiveDataError(f"{SMILE.as_posix()}: {exc}") from exc


def _backtest(path: str, result: WheelResult) -> LiveBacktest:
    metrics, window = result.summary.metrics, result.config.window
    return LiveBacktest(
        path=path,
        start=window.start.isoformat(),
        end=window.end.isoformat(),
        starting_cash=result.starting_cash,
        pnl=metrics.pnl,
        return_on_starting_cash=metrics.return_on_starting_cash,
        sharpe_annualized=metrics.sharpe_annualized,
        baseline_sharpe_annualized=result.summary.benchmarks.baseline_pmcc.sharpe_annualized,
    )


def wheel_run(
    symbol: str, wheels: Sequence[tuple[str, WheelResult]]
) -> tuple[str, WheelResult] | None:
    """The wheel's own run on `symbol` (run ID `wheel`, not a friction run), if exported."""
    return next(
        ((p, r) for p, r in wheels if r.manifest.symbol == symbol and r.manifest.run_id == "wheel"),
        None,
    )

"""One night of the live wheel: Sanji's book in, `open_orders.json` and a run-log row out (L2-03).

The order of a night (LIVE-SPEC › Trade rules):

1. **When:** a run on a trading day before its close, or past the session calendar, is refused
   and writes nothing (LD-24). Otherwise the session planned is the first after the run's date
   (L-S1), the same one the close snapshot plans.
2. **The book:** it must be current (L-B1) and readable (L-B2); every order already in the file
   must be valid (LD-22), and the root and `mkt/` copies must agree (LD-04).
3. **The decision:** with a put or call open, nothing (Sanji expires or assigns it). Otherwise, only
   for a week's first session (L-P1, L-C1): LSEG's close snapshot is pulled, with the strike rule's
   band, and the put (L-P2 to L-P4) or call (L-C2, L-C3) is picked and checked for liquidity
   (L-T1). The order is L-O1's. Every night that plans a week's first session does this, Friday
   through Sunday for a Monday, each replacing the last night's order (PO, LD-25).
4. **The file (PO, LD-19):** each order already in it stays until the week it's for has ended; a
   wheel order for the session planned tonight is replaced by tonight's decision, so a second run
   can't put on a second option. The same file is written at the root and under `mkt/` (LD-04).
5. **The checks:** LINV-02 to LINV-05 and LINV-07 hold before anything is written (LINV-01 is the
   order writer's, LINV-06 step 2's).
6. **The log:** one row a night, appended to `live/runs.jsonl`. A night that fails after step 1,
   whatever stops it, logs a failed row with the rule it failed under, writes no order, and
   raises (PO, LD-14).

A dry run decides and reports, and writes nothing.
"""

import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import final

from pmcc.data.files import replace_file
from pmcc.data.provider import ProviderOutageError
from pmcc.domain.calendar import SessionCalendar
from pmcc.domain.clock import to_et
from pmcc.domain.instruments import Right
from pmcc.domain.sessions import Session
from pmcc.live.book import Book, BookError, WheelState, check_current, read_book
from pmcc.live.config import RULE_IDS, LiveConfig, LiveConfigError, StrikeParams
from pmcc.live.names import ORDERS, RIGHT_NAMES, SANJI_DIR, dollars, quote_dollars
from pmcc.live.orders import Order, OrderError, order_id, read_orders, strike_token, write_orders
from pmcc.live.rules import Pick, liquid, secured, select
from pmcc.live.snapshot import CloseSnapshot, SnapshotError, last_completed, next_session

RUN_LOG = Path("live") / "runs.jsonl"
WHEEL_PREFIX = "wheel-"

# Tonight's close snapshot, asked with the strike rule's band; pulled only when it's needed.
SnapshotSource = Callable[[StrikeParams], CloseSnapshot]

# What can stop a night after its sessions are known. Each logs a failed row (LD-14).
FAILURES = (
    BookError,
    ProviderOutageError,
    SnapshotError,
    OrderError,
    LiveConfigError,
    OSError,
)


class LiveError(Exception):
    """The run can't go ahead (too early, past the calendar), or a check failed."""


@final
@dataclass(frozen=True, slots=True)
class Decision:
    """Tonight's decision: the rule that made it, why, and the order and pick if one was made."""

    rule: str
    reason: str
    order: Order | None = None
    pick: Pick | None = None


@final
@dataclass(frozen=True, slots=True)
class Night:
    """A run's outcome: the decision, the file it leaves, and its run-log row."""

    decision: Decision
    orders: tuple[Order, ...]
    row: dict[str, object]


def sessions_for(calendar: SessionCalendar, now: datetime) -> tuple[Session, Session]:
    """The last completed session and the one planned (L-S1). Raises `LiveError` on a trading
    day before its close, or outside the session calendar."""
    today = to_et(now).date()
    try:
        if calendar.is_session(today) and to_et(now) < calendar.session(today).close_bar_end:
            raise LiveError(
                f"it is {to_et(now):%Y-%m-%d %H:%M} ET, before today's close: the live wheel "
                "decides from the close, so run it after the session ends"
            )
        return last_completed(calendar, now), next_session(calendar, now)
    except ValueError as exc:
        raise LiveError(f"{today} is outside the session calendar: {exc}") from None


def run_night(
    root: Path,
    now: datetime,
    calendar: SessionCalendar,
    config: LiveConfig,
    snapshot: SnapshotSource,
    *,
    dry_run: bool = False,
) -> Night:
    """One night. Raises `LiveError` before anything is read (too early, past the calendar);
    after that, any failure is logged as a failed row and raised (LD-14)."""
    last, upcoming = sessions_for(calendar, now)
    book: Book | None = None
    decision: Decision | None = None
    try:
        check_current(root, last.day)
        existing = _existing_orders(root, calendar)
        book = read_book(root, config.cash)
        decision = decide(book, upcoming, calendar, config, snapshot)
        orders = merged(existing, decision, upcoming, calendar)
        check_night(book, decision, orders, last, upcoming, calendar, config)
        row = _row(now, last, upcoming, book, decision, orders)
        if not dry_run:
            for path in (root / ORDERS, root / SANJI_DIR / ORDERS):
                write_orders(path, orders)
    except (*FAILURES, LiveError) as exc:
        rule = _failed_rule(exc, book, decision)
        _log(root, _failed_row(now, last, upcoming, book, rule, _reason(exc)), dry_run)
        raise
    _log(root, row, dry_run)
    return Night(decision, orders, row)


def decide(
    book: Book,
    upcoming: Session,
    calendar: SessionCalendar,
    config: LiveConfig,
    snapshot: SnapshotSource,
) -> Decision:
    """Tonight's decision for `upcoming`. Pulls the snapshot only when an option may be sold."""
    if book.state is WheelState.PUT:
        return Decision("L-P1", "a put is open: Sanji expires it or assigns the shares")
    if book.state is WheelState.CALL:
        return Decision("L-C1", "a call is open: Sanji expires it or calls the shares away")
    right = Right.PUT if book.state is WheelState.CASH else Right.CALL
    timing = "L-P1" if right is Right.PUT else "L-C1"
    week_open = calendar.week_open(upcoming.day)
    if upcoming != week_open:
        return Decision(timing, f"{upcoming.day} is not its week's first session ({week_open.day})")
    strike_rule = "L-P3" if right is Right.PUT else "L-C3"
    snap = snapshot(config.strike(strike_rule))
    if snap.next_session != upcoming:
        raise LiveError(f"the snapshot plans {snap.next_session.day}, not {upcoming.day}")
    return _sell(snap, right, book, calendar, config)


def merged(
    existing: Sequence[Order], decision: Decision, upcoming: Session, calendar: SessionCalendar
) -> tuple[Order, ...]:
    """LD-19: the orders whose week hasn't ended, less any wheel order for `upcoming`, plus
    tonight's."""
    kept = [
        order
        for order in existing
        if calendar.week_final(order.for_).day >= upcoming.day
        and not (order.id.startswith(WHEEL_PREFIX) and order.for_ == upcoming.day)
    ]
    if decision.order is not None:
        kept.append(decision.order)
    return tuple(kept)


def check_night(
    book: Book,
    decision: Decision,
    orders: Sequence[Order],
    last: Session,
    upcoming: Session,
    calendar: SessionCalendar,
    config: LiveConfig,
) -> None:
    """LINV-02 to LINV-05 and LINV-07, before anything is written. Raises `LiveError`."""
    broken = _broken(book, decision, orders, last, upcoming, calendar, config)
    if broken:
        raise LiveError(f"{broken}; nothing was written")


def describe_night(night: Night, *, dry_run: bool) -> str:
    """The run in one line for the console and the Actions log: plain ASCII, no LSEG prices."""
    row, decision = night.row, night.decision
    text = (
        f"Planning {row['next_session']} from the close of {row['last_session']}, holding "
        f"{row['state']}: {decision.rule}: {decision.reason}."
    )
    if decision.pick is not None:
        text += f" Delta at the close {decision.pick.delta:+.2f}."
    text += f" {len(night.orders)} order(s) in {ORDERS}"
    return text + (" (dry run: nothing written)." if dry_run else ".")


def _broken(
    book: Book,
    decision: Decision,
    orders: Sequence[Order],
    last: Session,
    upcoming: Session,
    calendar: SessionCalendar,
    config: LiveConfig,
) -> str | None:
    if decision.rule not in RULE_IDS:
        return f"LINV-07: rule {decision.rule} isn't in configs/live.yaml"
    tonight = [o for o in orders if o.id.startswith(WHEEL_PREFIX) and o.for_ == upcoming.day]
    if len(tonight) > 1:
        return f"LINV-02: {len(tonight)} wheel orders for {upcoming.day}"
    order, pick = decision.order, decision.pick
    if order is None or pick is None:
        return None
    return _broken_order(book, order, pick, last, calendar, config)


def _broken_order(
    book: Book,
    order: Order,
    pick: Pick,
    last: Session,
    calendar: SessionCalendar,
    config: LiveConfig,
) -> str | None:
    wanted = WheelState.CASH if order.contract == "put" else WheelState.SHARES
    if book.state is not wanted:
        return f"LINV-02: a {order.contract} order while holding {book.state.value}"
    cash = config.cash_rule
    strike = pick.option.strike
    if order.contract == "put" and not secured(book.cash, strike, cash.contracts, cash.multiplier):
        return f"LINV-03: the put's strike x 100 is more than the cash ({dollars(book.cash)})"
    floor = book.cost_basis
    if order.contract == "call" and (floor is None or strike < floor):
        return f"LINV-04: the call's strike is below the cost basis ({floor})"
    if order.for_ <= last.day or not calendar.is_session(order.for_):
        return f"LINV-05: the order is for {order.for_}, not a session after {last.day}"
    return None


def _sell(
    snap: CloseSnapshot, right: Right, book: Book, calendar: SessionCalendar, config: LiveConfig
) -> Decision:
    name = RIGHT_NAMES[right]
    is_put = right is Right.PUT
    expiry_rule, strike_rule = ("L-P2", "L-P3") if is_put else ("L-C2", "L-C3")
    if not any(q.listed and q.option.right is right for q in snap.options):
        return Decision(expiry_rule, f"no {name} listed for the week's expiry, {snap.expiry}")
    floor = None if is_put else book.cost_basis
    if not is_put and floor is None:
        raise BookError("L-B2", "shares are held but the book has no cost basis")
    target = config.strike(strike_rule).target_delta
    pick = select(snap, right, target, config.risk_free.rate, calendar, floor)
    if pick is None:
        why = "with a delta at the close" if is_put else f"at or above the cost basis ({floor})"
        return Decision(strike_rule, f"no out-of-the-money {name} {why}")
    if not liquid(pick, config.max_spread):
        why = (
            f"the {name}'s spread is {pick.spread_pct:.1%} of its mid, over {config.max_spread:.0%}"
        )
        return Decision("L-T1", why, pick=pick)
    cash = config.cash_rule
    if is_put and not secured(book.cash, pick.option.strike, cash.contracts, cash.multiplier):
        why = f"cash {dollars(book.cash)} doesn't cover the {dollars(pick.option.strike)} put"
        return Decision("L-P4", why, pick=pick)
    order = _order(snap, pick, config)
    return Decision(
        "L-O1",
        f"sell {order.qty} {dollars(pick.option.strike)} {name} expiring {snap.expiry} at the mid",
        order,
        pick,
    )


def _order(snap: CloseSnapshot, pick: Pick, config: LiveConfig) -> Order:
    option = pick.option
    try:
        return Order.model_validate(
            {
                "id": order_id(snap.next_session.day, option.right, option.strike),
                "for": snap.next_session.day.isoformat(),
                "action": "SHT",
                "underlying": config.underlying_conid,
                "contract": RIGHT_NAMES[option.right],
                "expiry": snap.expiry.isoformat(),
                "strike": strike_token(option.strike),
                **config.order_fields(),
            }
        )
    except ValueError as exc:
        raise LiveError(f"L-O1 makes an order the language rejects: {exc}") from None


def _existing_orders(root: Path, calendar: SessionCalendar) -> tuple[Order, ...]:
    """The orders already in the file, which the root and `mkt/` copies must agree on (L-B2)."""
    root_file, sanji_file = root / ORDERS, root / SANJI_DIR / ORDERS
    try:
        orders = read_orders(root_file)
        if sanji_file.exists() and read_orders(sanji_file) != orders:
            raise BookError(
                "L-B2",
                f"{ORDERS} and {SANJI_DIR}/{ORDERS} differ: a write may have stopped half done",
            )
        for order in orders:
            calendar.week_final(order.for_)  # a date the calendar covers
    except (OrderError, ValueError) as exc:
        raise BookError("L-B2", f"an order already in {ORDERS} can't be kept: {exc}") from None
    return orders


def _failed_rule(exc: BaseException, book: Book | None, decision: Decision | None) -> str:
    """The rule a failed night is logged under (LINV-07)."""
    if isinstance(exc, BookError):
        return exc.rule
    if isinstance(exc, (ProviderOutageError, SnapshotError)):
        return "L-C3" if book is not None and book.state is WheelState.SHARES else "L-P3"
    if decision is not None:
        return decision.rule
    return "L-S1" if isinstance(exc, LiveError) else "L-O1"


def _reason(exc: BaseException) -> str:
    if isinstance(exc, (BookError, LiveError)):
        return str(exc)
    return f"{type(exc).__name__}: {exc}"


def _row(
    now: datetime,
    last: Session,
    upcoming: Session,
    book: Book,
    decision: Decision,
    orders: Sequence[Order],
) -> dict[str, object]:
    pick = decision.pick
    return {
        **_header(now, last, upcoming, book),
        "outcome": "order" if decision.order is not None else "no_order",
        "rule": decision.rule,
        "reason": decision.reason,
        "order_id": decision.order.id if decision.order is not None else None,
        "pick": None if pick is None else _pick(pick),
        "open_orders": len(orders),
    }


def _failed_row(
    now: datetime, last: Session, upcoming: Session, book: Book | None, rule: str, reason: str
) -> dict[str, object]:
    return {
        **_header(now, last, upcoming, book),
        "outcome": "failed",
        "rule": rule,
        "reason": reason,
        "order_id": None,
        "pick": None,
        "open_orders": None,
    }


def _header(
    now: datetime, last: Session, upcoming: Session, book: Book | None
) -> dict[str, object]:
    return {
        "run_at": to_et(now).isoformat(),
        "last_session": last.day.isoformat(),
        "next_session": upcoming.day.isoformat(),
        "state": None if book is None else book.state.value,
        "cash": None if book is None else dollars(book.cash),
        "cost_basis": None if book is None or book.cost_basis is None else dollars(book.cost_basis),
    }


def _pick(pick: Pick) -> dict[str, object]:
    # With its quote at the close, which the site shows (PO, LD-15); `spread` is (ask - bid) / mid,
    # as L-T1 reads it.
    return {
        "contract": RIGHT_NAMES[pick.option.right],
        "strike": strike_token(pick.option.strike),
        "expiry": pick.option.expiry.isoformat(),
        "delta": round(pick.delta, 4),
        "iv": round(pick.iv, 4),
        "bid": quote_dollars(pick.bid),
        "ask": quote_dollars(pick.ask),
        "mid": quote_dollars(pick.mid),
        "spread": round(pick.spread_pct, 4),
    }


def _log(root: Path, row: dict[str, object], dry_run: bool) -> None:
    if dry_run:
        return
    path = root / RUN_LOG
    before = path.read_bytes() if path.exists() else b""
    line = json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n"
    replace_file(path, before + line.encode("utf-8"))

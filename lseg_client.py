"""LSEG acquisition kit — the parts of options_surface_lab that are about LSEG, not about
any one assignment. Standalone: needs pandas, numpy and (only at pull time) lseg-data.

Everything here was learned against the live API between 2026-08-30 and 2026-09-18, on
UUUU (daily, expired options) and QQQ (hourly, weekly calls). LSEG-DATA-GUIDE.md explains
why each rule exists; read it before "simplifying" anything below.

Importing this module never touches the network. Only code running inside
``with lseg_session() as ld:`` does.
"""
from __future__ import annotations

import datetime as dt
import re
import warnings
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd

EXCHANGE_TZ = "America/New_York"

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------
@contextmanager
def lseg_session():
    """Open a Workspace desktop session and always close it.

    Reads ``lseg-data.config.json`` from the current working directory (run from the repo
    root). ``ld.open_session()`` does NOT raise when the handshake fails: it logs, returns,
    and every later request fails in ways that look like "no data". So the state is checked.
    """
    import lseg.data as ld  # local import: importing this module stays offline

    ld.open_session()
    try:
        state = str(getattr(ld.session.get_default(), "open_state", "unknown"))
        if not state.endswith("Opened"):
            raise RuntimeError(
                f"LSEG session did not open (state {state}). Workspace must be running AND "
                "signed in; if the proxy answers but the handshake hangs, restart Workspace. "
                "Nothing was requested."
            )
        yield ld
    finally:
        ld.close_session()


# ---------------------------------------------------------------------------
# Option RIC grammar:  {ROOT}{M}{DD}{YY}{SSSSS}.U[^{M}{YY}]
# ---------------------------------------------------------------------------
CALL_MONTHS = {chr(ord("A") + i): i + 1 for i in range(12)}  # A..L = Jan..Dec calls
PUT_MONTHS = {chr(ord("M") + i): i + 1 for i in range(12)}   # M..X = Jan..Dec puts
_CODE_TO_MONTH = {**CALL_MONTHS, **PUT_MONTHS}
_CODE_TO_CP = {**{k: "C" for k in CALL_MONTHS}, **{k: "P" for k in PUT_MONTHS}}
_CP_TO_CODE = {
    "C": {m: c for c, m in CALL_MONTHS.items()},
    "P": {m: c for c, m in PUT_MONTHS.items()},
}

RIC_RE = re.compile(
    r"^(?P<root>[A-Z]+)(?P<code>[A-X])(?P<day>\d{2})(?P<year>\d{2})"
    r"(?P<strike>\d{5})(?:\.U)?(?:\^[A-X]\d{2})?$",
    re.IGNORECASE,
)


def build_option_ric(root: str, expiry: dt.date, cp: str, strike: float,
                     expired: bool = True) -> str:
    """Build an OPRA-style option RIC.

    * Day is ALWAYS two digits (``05``), whatever the brief says — unpadded does not resolve.
    * Strike is five digits of hundredths, so max $999.99; anything larger raises rather
      than building a RIC that silently parses as a different contract.
    * ``expired=True`` adds the caret suffix. The suffix letter is the **call** month letter
      for BOTH rights (a June put is ``...R12...U^F26``, not ``^R26`` — ``^R26`` returns nothing).
    * ``expired=False`` is the live form (``QQQI182671500.U``). A recently expired contract
      may answer only to this one for a few days — ask both, see ``fetch_options``.
    """
    cp = str(cp).upper()
    if cp not in _CP_TO_CODE:
        raise ValueError(f"cp must be 'C' or 'P', got {cp!r}")
    hundredths = int(round(strike * 100))
    if not 0 < hundredths <= 99_999:
        raise ValueError(f"strike {strike} does not fit the 5-digit RIC strike field")
    code = _CP_TO_CODE[cp][expiry.month]
    yy = f"{expiry.year % 100:02d}"
    body = f"{root.upper()}{code}{expiry.day:02d}{yy}{hundredths:05d}"
    if not expired:
        return f"{body}.U"
    return f"{body}.U^{_CP_TO_CODE['C'][expiry.month]}{yy}"


def parse_option_ric(ric: str) -> dict | None:
    """Inverse of ``build_option_ric``; accepts either form. ``None`` if it is not an option RIC."""
    m = RIC_RE.match(str(ric).strip())
    if not m:
        return None
    code = m.group("code").upper()
    try:
        expiry = dt.date(2000 + int(m.group("year")), _CODE_TO_MONTH[code], int(m.group("day")))
    except ValueError:
        return None
    return {"ric": str(ric).strip(), "root": m.group("root").upper(), "cp": _CODE_TO_CP[code],
            "expiry": expiry, "strike": int(m.group("strike")) / 100.0}


def occ_symbol(root: str, expiry: dt.date, cp: str, strike: float) -> str:
    """OCC symbol: root padded to 6, YYMMDD, C/P, strike x1000 in 8 digits.
    ``QQQ   260918C00710000``. The padding is part of the symbol (HTML collapses it)."""
    return (f"{root.upper():<6}{expiry:%y%m%d}{str(cp).upper()}"
            f"{int(round(strike * 1000)):08d}")


def strike_band(low: float, high: float, step: float, pad: int = 4) -> list[float]:
    """Strikes covering [low, high] plus ``pad`` steps each side, on ``step``.

    Integer-cents arithmetic on purpose: a float ladder drifts, builds a RIC one cent off a
    real contract, and that returns nothing rather than erroring.
    """
    if step <= 0 or not (np.isfinite(low) and np.isfinite(high)) or high < low:
        raise ValueError(f"bad band {low}..{high} step {step}")
    s = int(round(step * 100))
    lo = max((int(np.floor(round(low * 100) / s)) - pad) * s, s)
    hi = (int(np.ceil(round(high * 100) / s)) + pad) * s
    return [c / 100.0 for c in range(lo, hi + s, s)]


# ---------------------------------------------------------------------------
# Time
# ---------------------------------------------------------------------------
def to_exchange_time(index, tz: str = EXCHANGE_TZ) -> pd.DatetimeIndex:
    """Intraday bars come back tz-naive in **UTC**, stamped at the bar's **start**.
    Localise and convert; never hardcode a UTC hour (15:00 ET is 19:00 UTC in EDT, 20:00 in EST).
    Daily bars are dates — do not pass them through here."""
    index = pd.DatetimeIndex(index)
    if index.tz is None:
        index = index.tz_localize("UTC")
    return index.tz_convert(tz)


# ---------------------------------------------------------------------------
# History requests
# ---------------------------------------------------------------------------
def history(ld, universe, fields, start, end, interval="daily"):
    """Fail-soft ``get_history`` → ``(df | None, error | None)``. A guessed RIC must never crash a pull."""
    try:
        return ld.get_history(universe=list(universe), fields=list(fields),
                              start=str(start), end=str(end), interval=interval), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def to_long(df: pd.DataFrame | None, rics, fields, intraday: bool) -> pd.DataFrame:
    """Melt any ``get_history`` shape into ``(ts, ric, field, value)``, dropping empty cells.

    LSEG changes the column shape with the request: MultiIndex (RIC, field) or (field, RIC)
    for many RICs; flat fields for one RIC; flat RICs when one field populated. The RIC axis
    is identified by matching the *requested* RICs, never by position.
    """
    cols = ["ts", "ric", "field", "value"]
    if df is None or getattr(df, "empty", True):
        return pd.DataFrame(columns=cols)
    wanted, fields = {str(r) for r in rics}, {str(f) for f in fields}
    if df.columns.nlevels == 2:
        lvl = 0 if {str(c) for c in df.columns.get_level_values(0)} & wanted else 1
        pieces = [(str(c[lvl]), str(c[1 - lvl]), df[c]) for c in df.columns]
    elif not {str(c) for c in df.columns} & fields:               # many RICs, one field
        name = str(df.columns.name or next(iter(fields)))
        pieces = [(str(c), name, df[c]) for c in df.columns]
    elif len(wanted) == 1:                                        # one RIC, many fields
        only = next(iter(wanted))
        pieces = [(only, str(c), df[c]) for c in df.columns]
    else:
        warnings.warn("bare field columns for several RICs; cannot attribute, dropping",
                      RuntimeWarning)
        return pd.DataFrame(columns=cols)

    index = to_exchange_time(df.index) if intraday else pd.DatetimeIndex(df.index)
    out = []
    for ric, field, series in pieces:
        if field not in fields:
            continue
        v = pd.to_numeric(pd.Series(series.to_numpy(), index=index), errors="coerce").dropna()
        if not v.empty:
            out.append(pd.DataFrame({"ts": v.index, "ric": ric, "field": field,
                                     "value": v.to_numpy()}))
    return pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=cols)


def fetch_universe(ld, rics, fields, start, end, interval="daily", batch_size=25):
    """Batched pull. A batch rejected whole is retried one RIC at a time, so one bad guess
    does not cost the other 24. Returns ``(long_rows, errors)``.

    NB: a batch that answers *partially* raises nothing — compare the RICs in the result
    against what you asked for (``fetch_options`` does) or misses leave no trace.
    """
    intraday = interval not in ("daily", "weekly", "monthly")
    rics, frames, errors = list(rics), [], []
    for i in range(0, len(rics), batch_size):
        batch = rics[i:i + batch_size]
        df, err = history(ld, batch, fields, start, end, interval)
        if df is not None:
            frames.append(to_long(df, batch, fields, intraday))
            continue
        errors.append({"universe": batch, "error": err})
        for ric in batch:
            one, one_err = history(ld, [ric], fields, start, end, interval)
            if one is not None:
                frames.append(to_long(one, [ric], fields, intraday))
            else:
                errors.append({"universe": [ric], "error": one_err})
    long = (pd.concat(frames, ignore_index=True) if frames
            else pd.DataFrame(columns=["ts", "ric", "field", "value"]))
    return long, errors


def fetch_options(ld, root, expiry, strikes, fields, start, end, cp="C",
                  interval="daily", batch_size=25):
    """Pull one expiry's contracts, asking each strike under the caret form first and then
    the live form for whatever did not answer. Which form a contract answers to depends on
    how long ago it expired, and the changeover is several days wide — do not predict it.

    Returns ``(long_rows, diagnostics)`` where diagnostics carries ``ric_form_used``
    (ric -> 'expired'|'live'), ``unanswered`` (contracts neither form returned, canonical
    caret spelling, one per contract), ``requested`` and ``errors``.
    """
    pending, frames = list(strikes), []
    diag = {"ric_form_used": {}, "unanswered": [], "requested": [], "errors": []}
    for form, expired in (("expired", True), ("live", False)):
        if not pending:
            break
        rics = {build_option_ric(root, expiry, cp, k, expired=expired): k for k in pending}
        diag["requested"].extend(rics)
        long, errs = fetch_universe(ld, list(rics), fields, start, end, interval, batch_size)
        diag["errors"].extend(errs)
        answered = set(long["ric"].astype(str)) if not long.empty else set()
        if answered:
            frames.append(long)
        diag["ric_form_used"].update({r: form for r in rics if r in answered})
        pending = [k for r, k in rics.items() if r not in answered]
    diag["unanswered"] = [build_option_ric(root, expiry, cp, k, expired=True) for k in pending]
    long = (pd.concat(frames, ignore_index=True) if frames
            else pd.DataFrame(columns=["ts", "ric", "field", "value"]))
    return long, diag


def to_wide(long: pd.DataFrame) -> pd.DataFrame:
    """``(ts, ric, field, value)`` → one row per (ts, ric), one column per field, plus
    ``expiry``/``strike``/``cp`` parsed off the RIC that actually answered (null for stock)."""
    if long.empty:
        return pd.DataFrame(columns=["ts", "ric", "expiry", "strike", "cp"])
    wide = long.groupby(["ts", "ric", "field"])["value"].last().unstack("field").reset_index()
    wide.columns.name = None
    parsed = [parse_option_ric(r) for r in wide["ric"]]
    wide["expiry"] = [p["expiry"] if p else None for p in parsed]
    wide["strike"] = [p["strike"] if p else np.nan for p in parsed]
    wide["cp"] = [p["cp"] if p else None for p in parsed]
    return wide.sort_values(["ts", "ric"]).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Cache discipline
# ---------------------------------------------------------------------------
def refuse_overwrite(path: str | Path) -> Path:
    """Call before a pull. Pulled data is an artifact: commit it, never silently regenerate it."""
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"{path} exists. Rename it first if you really mean to re-pull.")
    return path

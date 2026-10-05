"""Starting cash (Spec › E-L4; DEC-30): each symbol's own, E-L4's `cash_multiple` × that symbol's
most expensive first long-leg entry cost, rounded up to its `cash_round_to` (2× and $5,000), with
the basis it was calibrated from. Each symbol's runs are an account of their own, so one symbol's
value never depends on another's (PO, 2026-10-05).

`pmcc calibrate` works the values out and writes them into `configs/universe.yaml` as a block of
its own, at the end of the file (`render_block`, `with_block`); the universe loader validates it. A
symbol's value is provisional until it has been calibrated under both strategies, and final after;
calibrating another symbol never changes it (`StartingCash.merged`).
"""

import re
from collections import Counter
from collections.abc import Iterable, Sequence
from typing import Self

import yaml
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from pmcc.config.fields import DollarMoney
from pmcc.config.yaml_file import parse_yaml
from pmcc.domain.money import Money

CALIBRATED_STRATEGIES = ("baseline_pmcc", "quant_pmcc")  # DEC-30: both strategies, no variants

MARKER = "# ── Starting cash: written by `pmcc calibrate`"
_HEADER = f"""{MARKER} (Spec › E-L4; DEC-30) ────────────────────────────
# Each symbol's own: E-L4's cash_multiple × that symbol's most expensive first long-leg entry cost
# (E-L1: fill × 100 × qty + fees, at spread_capture 0), rounded up to its cash_round_to. Every run
# on the symbol uses it unchanged. Each entry is one run's first long-leg entry, measured at
# `calibration_cash`, which is never a run's starting cash; every run was then checked to make all
# its entries at its symbol's `value` (no E-L4 block). A symbol stays `provisional` until it is
# calibrated under both strategies. Don't edit this block: `pmcc calibrate` replaces a provisional
# symbol and adds a missing one, `pmcc calibrate --check` recomputes it byte for byte, and a final
# symbol is only ever removed by hand.
"""
_KEY = re.compile(r"^starting_cash\s*:", re.MULTILINE)


def starting_cash_for(costs: Iterable[Money], multiple: int, round_to: Money) -> Money:
    """E-L4's rule: `multiple` × the largest cost, rounded up to a multiple of `round_to`."""
    need = max(costs) * multiple
    return round_to * -(-need.units // round_to.units)  # integer ceiling division


class CalibrationEntry(BaseModel):
    """One run's first long-leg entry: what it bought, when, and what it cost."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: str = Field(min_length=1)
    time: AwareDatetime
    contract: str = Field(min_length=1)  # the RIC its cache answered with
    cost: DollarMoney  # fill × 100 × qty + fees


class SymbolCash(BaseModel):
    """One symbol's starting cash, and the entries it was calibrated from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str = Field(min_length=1)
    value: DollarMoney
    provisional: bool
    entries: tuple[CalibrationEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _complete_or_provisional(self) -> Self:
        twice = sorted(t for t, n in Counter(e.strategy for e in self.entries).items() if n > 1)
        if twice:
            raise ValueError(f"{self.symbol}'s starting_cash lists a strategy more than once: "
                             f"{twice}")  # fmt: skip
        others = sorted({e.strategy for e in self.entries} - set(CALIBRATED_STRATEGIES))
        if others:
            raise ValueError(
                f"starting_cash is calibrated on {CALIBRATED_STRATEGIES}, not {others}"
            )
        if any(e.cost.units <= 0 for e in self.entries):
            raise ValueError(f"{self.symbol}: a first long-leg entry costs more than $0")
        if self.provisional != bool(self.missing()):
            state = "provisional" if self.provisional else "final"
            raise ValueError(f"{self.symbol}'s starting_cash is marked {state}, but it lacks "
                             f"{self.missing() or 'nothing'}")  # fmt: skip
        return self

    def missing(self) -> list[str]:
        """The calibrated strategies this symbol's value wasn't measured under."""
        done = {e.strategy for e in self.entries}
        return [t for t in CALIBRATED_STRATEGIES if t not in done]


class StartingCash(BaseModel):
    """Each calibrated symbol's starting cash, under one E-L4 rule."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    cash_multiple: int = Field(ge=1)  # E-L4's params the values were set by
    cash_round_to: DollarMoney
    calibration_cash: DollarMoney
    symbols: tuple[SymbolCash, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _follows_the_rule(self) -> Self:
        twice = sorted(s for s, n in Counter(c.symbol for c in self.symbols).items() if n > 1)
        if twice:
            raise ValueError(f"starting_cash lists a symbol more than once: {twice}")
        if self.cash_round_to.units <= 0:
            raise ValueError("cash_round_to is more than $0")
        for cash in self.symbols:
            expected = starting_cash_for(
                (e.cost for e in cash.entries), self.cash_multiple, self.cash_round_to
            )
            if cash.value != expected:
                raise ValueError(
                    f"{cash.symbol}'s starting_cash {cash.value.to_dollars()} isn't "
                    f"{self.cash_multiple}× its most expensive entry rounded up to "
                    f"{self.cash_round_to.to_dollars()} ({expected.to_dollars()})"
                )
        return self

    def of(self, symbol: str) -> SymbolCash | None:
        """The symbol's starting cash, or None if it isn't calibrated yet."""
        return next((c for c in self.symbols if c.symbol == symbol), None)

    def merged(self, new: "StartingCash", order: Sequence[str]) -> "StartingCash":
        """This block with `new`'s symbols in place of its own, every other symbol kept, in
        `order`'s symbol order (others after, by name). Raises `ValueError` if the two were
        calibrated under different rules. `pmcc calibrate` never passes a final symbol here to
        write (DEC-30), only to check."""
        if self.rule != new.rule:
            raise ValueError(f"the starting cash was calibrated under E-L4 {self.rule}, not "
                             f"{new.rule}; remove the block by hand to recalibrate every "
                             "symbol")  # fmt: skip
        fresh = {c.symbol for c in new.symbols}
        kept = [c for c in self.symbols if c.symbol not in fresh]
        return self.model_copy(update={"symbols": in_order([*kept, *new.symbols], order)})

    @property
    def rule(self) -> tuple[int, str, str]:
        return (self.cash_multiple, str(self.cash_round_to.to_dollars()),
                str(self.calibration_cash.to_dollars()))  # fmt: skip


def in_order(symbols: Iterable[SymbolCash], order: Sequence[str]) -> tuple[SymbolCash, ...]:
    """`symbols` in `order`'s symbol order, any it doesn't name after, by name."""

    def rank(cash: SymbolCash) -> tuple[int, str]:
        return (order.index(cash.symbol) if cash.symbol in order else len(order)), cash.symbol

    return tuple(sorted(symbols, key=rank))


def render_block(cash: StartingCash) -> str:
    """The block `pmcc calibrate` writes: its header comment, then the `starting_cash` key."""
    body = yaml.safe_dump(
        {"starting_cash": cash.model_dump(mode="json")},
        sort_keys=False,
        allow_unicode=True,
        width=100,
    )
    return _HEADER + body


def with_block(text: str, block: str) -> str:
    """`text` (a universe file) with its calibration block replaced by `block`, or `block` appended.

    The block is always the file's last key, so everything before its marker is kept byte for byte.
    Raises `ValueError` for a `starting_cash` set by hand (no marker) or anything written after the
    block, which replacing it would lose.
    """
    at = text.find(MARKER)
    if at == -1:
        if _KEY.search(text):
            raise ValueError(
                "starting_cash is set without pmcc calibrate's block; remove it and calibrate"
            )
        return text.rstrip("\n") + "\n\n" + block
    tail = parse_yaml(text[at:])
    if not isinstance(tail, dict) or list(tail) != ["starting_cash"]:  # pyright: ignore[reportUnknownArgumentType]
        raise ValueError("configs/universe.yaml has keys after the starting_cash block")
    return text[:at] + block

"""Starting cash (Spec › E-L4; DEC-30): E-L4's `cash_multiple` × the most expensive first long-leg
entry cost in the universe, rounded up to its `cash_round_to` (2× and $5,000), with the basis it
was calibrated from.

`pmcc calibrate` works the value out and writes it into `configs/universe.yaml` as a block of its
own, at the end of the file (`render_block`, `with_block`); the universe loader validates it. The
value is provisional until every universe symbol has been calibrated under both strategies.
"""

import re
from collections import Counter
from collections.abc import Iterable
from typing import Self

import yaml
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from pmcc.config.fields import DollarMoney
from pmcc.config.yaml_file import parse_yaml
from pmcc.domain.money import Money

CALIBRATED_STRATEGIES = ("baseline_pmcc", "quant_pmcc")  # DEC-30: both strategies, no variants

MARKER = "# ── Starting cash: written by `pmcc calibrate`"
_HEADER = f"""{MARKER} (Spec › E-L4; DEC-30) ────────────────────────────
# E-L4's cash_multiple × the most expensive first long-leg entry cost (E-L1: fill × 100 × qty +
# fees, at spread_capture 0), rounded up to its cash_round_to. Every run uses it unchanged. Each
# entry is one run's first long-leg entry, measured at `calibration_cash`, which is never a run's
# starting cash; every run was then checked to make all its entries at `value` (no E-L4 block).
# `provisional` stays true until every symbol is calibrated under both strategies. Don't edit this
# block: `pmcc calibrate` replaces a provisional one, `pmcc calibrate --check` recomputes it byte
# for byte, and a final one is only ever removed by hand.
"""
_KEY = re.compile(r"^starting_cash\s*:", re.MULTILINE)


def starting_cash_for(costs: Iterable[Money], multiple: int, round_to: Money) -> Money:
    """E-L4's rule: `multiple` × the largest cost, rounded up to a multiple of `round_to`."""
    need = max(costs) * multiple
    return round_to * -(-need.units // round_to.units)  # integer ceiling division


class CalibrationEntry(BaseModel):
    """One run's first long-leg entry: what it bought, when, and what it cost."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    symbol: str = Field(min_length=1)
    strategy: str = Field(min_length=1)
    time: AwareDatetime
    contract: str = Field(min_length=1)  # the RIC its cache answered with
    cost: DollarMoney  # fill × 100 × qty + fees

    @property
    def pair(self) -> tuple[str, str]:
        return self.symbol, self.strategy


class StartingCash(BaseModel):
    """Every run's starting cash, and the entries it was calibrated from."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: DollarMoney
    provisional: bool
    cash_multiple: int = Field(ge=1)  # E-L4's params the value was set by
    cash_round_to: DollarMoney
    calibration_cash: DollarMoney
    entries: tuple[CalibrationEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _follows_the_rule(self) -> Self:
        twice = sorted(p for p, n in Counter(e.pair for e in self.entries).items() if n > 1)
        if twice:
            raise ValueError(f"starting_cash lists a symbol and strategy more than once: {twice}")
        others = sorted({e.strategy for e in self.entries} - set(CALIBRATED_STRATEGIES))
        if others:
            raise ValueError(
                f"starting_cash is calibrated on {CALIBRATED_STRATEGIES}, not {others}"
            )
        if any(e.cost.units <= 0 for e in self.entries) or self.cash_round_to.units <= 0:
            raise ValueError("a first long-leg entry, and cash_round_to, are more than $0")
        expected = starting_cash_for(
            (e.cost for e in self.entries), self.cash_multiple, self.cash_round_to
        )
        if self.value != expected:
            raise ValueError(
                f"starting_cash {self.value.to_dollars()} isn't {self.cash_multiple}× its most "
                f"expensive entry rounded up to {self.cash_round_to.to_dollars()} "
                f"({expected.to_dollars()})"
            )
        return self

    def missing(self, symbols: Iterable[str]) -> list[tuple[str, str]]:
        """The universe's symbol and strategy pairs this value wasn't calibrated on."""
        return missing_pairs(self.entries, symbols)


def missing_pairs(entries: Iterable[CalibrationEntry],
                  symbols: Iterable[str]) -> list[tuple[str, str]]:  # fmt: skip
    """Each of `symbols` under each calibrated strategy, less those `entries` cover."""
    done = {e.pair for e in entries}
    return [(s, t) for s in symbols for t in CALIBRATED_STRATEGIES if (s, t) not in done]


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

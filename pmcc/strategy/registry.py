"""Kinds → code, and a `StrategyConfig` → a runnable `Strategy` (ARCHITECTURE §5.3; DEC-53, DEC-90).

Every kind `pmcc.config.kinds.KINDS` registers has a factory here, and a test holds the two key
sets equal. A factory builds the rule object from its params; `build_strategy` places each by its
rule ID. "Off" is absence: an optional rule the config leaves out isn't built (DEC-53).

E-L1, E-S1, E-S4, X-S4, X-S5 and X-E1 are timing and bookkeeping rules the engine loop enforces
(DEC-20, DEC-34); their factories return markers, so the rule is present, its ID is valid, and
the loop has one place to read it from.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import final

from pmcc.config import kinds as k
from pmcc.config.kinds import Params
from pmcc.config.strategy import StrategyConfig
from pmcc.domain.rules import RuleId
from pmcc.strategy.exits import (
    DefensiveDelta,
    ExitRule,
    ExpiryResolver,
    FridayCheck,
    LongDeltaReset,
    LongDteRoll,
    TakeProfit,
)
from pmcc.strategy.gates import (
    EventRatioGate,
    Gate,
    MinPremiumGate,
    NoQuoteGate,
    StructuralConstraint,
    StructuralGate,
    VrpGate,
)
from pmcc.strategy.selectors import (
    CheapestReplacement,
    DteRangeExpiry,
    ExpectedMoveStrike,
    LongExpiryRule,
    LongSelector,
    LongStrikeRule,
    NearestDeltaLong,
    NearestDeltaShort,
    NearestDteExpiry,
    ShortExpiryRule,
    ShortSelector,
    ShortStrikeRule,
    WeekFinalExpiry,
)
from pmcc.strategy.trigger import EntryTrigger, FixedBarTrigger, SpreadTrigger


@final
@dataclass(frozen=True, slots=True)
class Marker:
    """A rule the engine loop enforces: present, with its ID, and nothing to compute."""

    rule_id: RuleId


@final
@dataclass(frozen=True, slots=True)
class Strategy:
    """A strategy, built: every rule object the engine loop calls, in spec order."""

    config: StrategyConfig
    long_selector: LongSelector
    short_selector: ShortSelector
    trigger: EntryTrigger  # E-T1
    constraint: StructuralConstraint
    long_contracts: int  # E-L4; E-S4 matches it
    no_quote: NoQuoteGate
    gates: tuple[Gate, ...]  # G-2 to G-5, those present, in spec order
    long_exits: tuple[ExitRule, ...]  # X-L1, X-L2
    short_exits: tuple[ExitRule, ...]  # X-S1 (if present), X-S2, X-S3
    friday_check: FridayCheck
    expiry: ExpiryResolver

    @property
    def rule_ids(self) -> frozenset[RuleId]:
        return self.config.rule_ids


type Factory = Callable[[Params, StrategyConfig], object]


def _marker(rule_id: str) -> Factory:
    return lambda _params, _config: Marker(RuleId(rule_id))


def _p[P: Params](params: Params, kind: type[P]) -> P:
    if not isinstance(params, kind):
        raise TypeError(f"expected {kind.__name__} params, got {type(params).__name__}")
    return params


def _fixed_bar_trigger(params: Params, _: StrategyConfig) -> FixedBarTrigger:
    p = _p(params, k.FixedBarTrigger)
    return FixedBarTrigger(p.bar, SpreadTrigger(p.long_max_spread, p.short_max_spread))


def _friday_check(params: Params, _: StrategyConfig) -> FridayCheck:
    p = _p(params, k.FridayCheck)
    return FridayCheck(p.check_by, p.em_buffer)


def _take_profit(params: Params, config: StrategyConfig) -> TakeProfit:
    """X-S1 runs until the Friday check, so it reads X-S3's check time: move one, move both."""
    check = _p(config.rule(RuleId("X-S3")).params, k.FridayCheck)
    return TakeProfit(_p(params, k.TakeProfit).max_credit_fraction, check.check_by)


FACTORIES: Mapping[str, Factory] = MappingProxyType(
    {
        "spread_trigger": lambda p, _: SpreadTrigger(
            _p(p, k.SpreadTrigger).long_max_spread, _p(p, k.SpreadTrigger).short_max_spread
        ),
        "fixed_bar_trigger": _fixed_bar_trigger,
        "first_session_retry": _marker("E-L1"),
        "nearest_dte_expiry": lambda p, _: NearestDteExpiry(_p(p, k.NearestDteExpiry).target_dte),
        "dte_range_expiry": lambda p, _: DteRangeExpiry(
            _p(p, k.DteRangeExpiry).min_dte, _p(p, k.DteRangeExpiry).max_dte
        ),
        "nearest_delta_long": lambda p, _: NearestDeltaLong(_p(p, k.NearestDelta).target_delta),
        "cheapest_replacement": lambda p, _: CheapestReplacement(
            _p(p, k.DeltaBand).min_delta, _p(p, k.DeltaBand).max_delta
        ),
        "fixed_contracts": lambda p, _: _p(p, k.FixedContracts).contracts,
        "week_open_short": _marker("E-S1"),
        "week_final_expiry": lambda _p_, _: WeekFinalExpiry(),
        "nearest_delta_short": lambda p, _: NearestDeltaShort(_p(p, k.NearestDelta).target_delta),
        "expected_move_strike": lambda p, _: ExpectedMoveStrike(_p(p, k.ExpectedMoveStrike).k),
        "match_long_qty": _marker("E-S4"),
        "strike_covers_debit": lambda _p_, _: StructuralConstraint(),
        "no_quote_gate": lambda _p_, _: NoQuoteGate(),
        "structural_gate": lambda _p_, _: StructuralGate(StructuralConstraint()),
        "event_ratio_gate": lambda p, _: EventRatioGate(_p(p, k.MaxRatio).max_ratio),
        "vrp_gate": lambda p, _: VrpGate(_p(p, k.MinRatio).min_ratio),
        "min_premium_gate": lambda p, _: MinPremiumGate(_p(p, k.MinPremium).min_mid),
        "take_profit": _take_profit,
        "defensive_delta": lambda p, _: DefensiveDelta(_p(p, k.MaxDelta).max_delta),
        "friday_check": _friday_check,
        "expire_otm": _marker("X-S4"),
        "missed_assignment": _marker("X-S5"),
        "long_delta_reset": lambda p, _: LongDeltaReset(_p(p, k.MinDelta).min_delta),
        "long_dte_roll": lambda p, _: LongDteRoll(_p(p, k.MinDte).min_dte),
        "end_of_backtest": _marker("X-E1"),
    }
)
"""Every kind's factory; the key set is `KINDS`'s."""


def build_strategy(config: StrategyConfig) -> Strategy:
    """The strategy `config` describes."""
    built = {r.id: FACTORIES[r.kind](r.params, config) for r in config.rules}

    def get[T](rule_id: str, kind: type[T]) -> T:
        rule = built[RuleId(rule_id)]
        if not isinstance(rule, kind):
            raise TypeError(f"{rule_id} built a {type(rule).__name__}, not a {kind.__name__}")
        return rule

    def present[T](ids: tuple[str, ...], kind: type[T]) -> tuple[T, ...]:
        return tuple(get(i, kind) for i in ids if RuleId(i) in built)

    constraint = get("E-S5", StructuralConstraint)
    return Strategy(
        config=config,
        long_selector=LongSelector(get("E-L2", LongExpiryRule), get("E-L3", LongStrikeRule)),
        short_selector=ShortSelector(get("E-S2", ShortExpiryRule), get("E-S3", ShortStrikeRule)),
        trigger=get("E-T1", EntryTrigger),
        constraint=constraint,
        long_contracts=get("E-L4", int),
        no_quote=get("G-1", NoQuoteGate),
        gates=present(("G-2", "G-3", "G-4", "G-5"), Gate),
        long_exits=present(("X-L1", "X-L2"), ExitRule),
        short_exits=present(("X-S1", "X-S2", "X-S3"), ExitRule),
        friday_check=get("X-S3", FridayCheck),
        expiry=ExpiryResolver(),
    )

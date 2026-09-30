"""Synthetic markets generated once per test session, keyed by name (the `synthetic` fixture)."""

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pmcc.data.load import SymbolData, load_symbol
from pmcc.engine.market_view import MarketData
from tests.fixtures.synthetic.market import RATE, Market, SyntheticSpec, generate


@dataclass(frozen=True, slots=True)
class Loaded:
    """A generated market, as the loader read it, and priced for MarketView."""

    market: Market
    symbol: SymbolData
    data: MarketData


class SyntheticMarkets:
    """Generates, loads and prices a market the first time its name is asked for, then reuses it.
    A name must always stand for the same builder and arguments."""

    def __init__(self, root: Path) -> None:
        self._root = root
        self._markets: dict[str, Loaded] = {}

    def get(self, name: str, build: Callable[[], SyntheticSpec]) -> Loaded:
        if name not in self._markets:
            self._markets[name] = load(build(), self._root / name)
        return self._markets[name]


def load(spec: SyntheticSpec, root: Path) -> Loaded:
    """Generate `spec` under `root`, load it and price it."""
    written = generate(spec, root)
    loaded = load_symbol(root, spec.symbol, written.calendar)
    data = MarketData.build(loaded.stock, loaded.chains, loaded.calendar, RATE, spec.symbol)
    return Loaded(written, loaded, data)

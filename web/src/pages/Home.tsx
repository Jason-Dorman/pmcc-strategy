// The home page, `#/` (UI-SPEC §6 › Home; PO, LD-36, LD-37): a headline over a tile per strategy,
// the volatility thesis first (PO, TD-28), then the live wheel, on a slowly moving background. Each tile is a kicker, the strategy's
// name, one big figure from its own file, a line on what it does, and its pages. A modern break
// from the terminal look behind it (PO, LD-37): rounded, layered tiles, larger type, no panel
// chrome. From `thesis.json` (the thesis's tracker), `live.json` (the live wheel, and the wheel backtest's result it carries) and
// `universe/headline.json` (the PMCC's).
import type { ReactNode } from "react";
import { useId } from "react";
import { Link } from "react-router-dom";

import { pageOf, pagePath, STRATEGIES, type StrategyKey } from "../app/pages";
import { longDate, shortDate } from "../components/charts/axis";
import { useIndex } from "../data/IndexContext";
import type { Loaded } from "../data/state";
import { useLive, useThesis, useUniverseFile } from "../data/useRun";
import { moneySigned } from "../format/money";
import { iv, orDash, pct, ratio } from "../format/number";
import { isStale, volPoints } from "../format/thesis";
import { timeET } from "../format/time";
import type { Headline } from "../types/generated/headline";
import type { Live } from "../types/generated/live";
import type { Thesis } from "../types/generated/thesis";
import { pickFor } from "./live/sections";
import { tileStates } from "./thesis/versions";

/** The value once loaded; nothing while loading or when the file is missing. */
function ready<T>(state: Loaded<T>): T | undefined {
  return state.kind === "ready" ? state.value : undefined;
}

function span(start: string, end: string): string {
  return `${shortDate(start)} – ${shortDate(end)}`;
}

interface TileProps {
  strategy: StrategyKey;
  kicker: string;
  figure: string;
  /** What the figure is in, beside it. */
  unit?: string;
  detail: string;
  blurb: string;
  symbol: string | undefined;
  live?: boolean;
}

/** The forward test's figure is a sentence, so it's set a step smaller to fit a line. */
function figureClass(sentence: boolean): string {
  return sentence ? "pm-tile-figure pm-tile-words" : "pm-tile-figure";
}

function Figure({ sentence, figure, unit }: { sentence: boolean; figure: string;
                                              unit: string | undefined }) {
  return (
    <div className={figureClass(sentence)}>
      {figure}{unit && <span className="pm-tile-unit"> {unit}</span>}
    </div>
  );
}

/** A strategy's tile: its name links to its first page, its pages are the chips below. */
function Tile({ strategy, kicker, figure, unit, detail, blurb, symbol,
                live = false }: TileProps) {
  const id = useId();
  const s = STRATEGIES.find((x) => x.key === strategy);
  const pages = (s?.menu ?? []).map(pageOf);
  const [first] = pages;
  return (
    <section className="pm-tile" aria-labelledby={id}>
      <div className="pm-tile-kicker">
        {live && <span className="pm-live-dot" aria-hidden="true" />}
        {kicker}
      </div>
      <h2 id={id} className="pm-tile-name">
        {first ? <Link to={pagePath(first, symbol)}>{s?.label}</Link> : s?.label}
      </h2>
      <Figure sentence={live} figure={figure} unit={unit} />
      <div className="pm-tile-detail">{detail}</div>
      <p className="pm-tile-blurb">{blurb}</p>
      <ul className="pm-tile-pages" aria-label={`${s?.label ?? strategy} pages`}>
        {pages.map((page) => (
          <li key={page.key}><Link to={pagePath(page, symbol)}>{page.label} →</Link></li>
        ))}
      </ul>
    </section>
  );
}

/** The thesis's tile (PO, TD-28): VIX minus the 30-day forecast, signed, in volatility points,
 * or "Unavailable", never zero; each version's state (TD-33); and the session it's as of. */
function thesisTile(state: Loaded<Thesis>): TileProps {
  const base = {
    strategy: "thesis" as const, kicker: "Daily thesis tracker", symbol: undefined,
    blurb: "VIX minus the 30-day volatility forecast: the research measure the thesis tracks, not "
      + "an expected trading return.",
  };
  if (state.kind === "loading") return { ...base, figure: "—", detail: "" };
  const t = ready(state);
  if (t === undefined) return { ...base, figure: "Unavailable", detail: "" };
  const gap = t.current?.forecast_gap_vol ?? null;
  return {
    ...base,
    ...(gap === null ? { figure: "Unavailable" }
      : { figure: volPoints(gap), unit: "volatility points" }),
    detail: [tileStates(t.comparison),
             t.data_through && `Data through ${longDate(t.data_through)}`,
             isStale(t) && "Stale: an update is overdue"].filter(Boolean).join(" · "),
  };
}

/** This week's trade as a story (PO, LD-38): the option the open order sells, as LSEG picked
 * it at the close (LD-35), with its delta, IV and expiry; or that none is open. */
function weekTrade(live: Live | undefined): { figure: string; detail: string } {
  if (!live) return { figure: "—", detail: "" };
  const [order] = live.orders;
  if (!order) {
    return { figure: "No trade open", detail: "The next put is sold for a week's first session" };
  }
  const pick = pickFor(order, live.runs);
  const expires = order.expiry ? `expires ${shortDate(order.expiry)}` : "";
  if (!pick) return { figure: `Selling a ${order.contract}`, detail: expires };
  return { figure: `Selling a $${pick.strike} ${pick.contract}`,
           detail: [`Delta ${ratio(pick.delta)}`, `IV ${iv(pick.iv)}`, expires]
             .filter(Boolean).join(" · ") };
}

function liveTile(live: Live | undefined, symbol: string | undefined): TileProps {
  return { strategy: "live", kicker: "Forward test · nightly", ...weekTrade(live), symbol,
           live: true,
           blurb: `Each week it sells one ${symbol ?? ""} option; the course's order system `
             + "fills it." };
}

function wheelTile(live: Live | undefined, symbol: string | undefined): TileProps {
  const b = live?.backtest;
  return {
    strategy: "wheel", kicker: b ? `Backtest · ${span(b.start, b.end)}` : "Backtest", symbol,
    figure: b ? moneySigned(b.pnl) : "—",
    detail: b ? `${pct(b.return_on_starting_cash)} · Sharpe ${orDash(b.sharpe_annualized, ratio)}`
      : "",
    blurb: "Cash-secured weekly puts, then covered calls once assigned, on hourly LSEG data.",
  };
}

function pmccTile(headline: Headline | undefined, symbol: string | undefined,
                  window: { start: string; end: string } | undefined): TileProps {
  const rows = headline?.rows.filter((r) => r.symbol === symbol) ?? [];
  const base = rows.find((r) => r.strategy_id === "baseline_pmcc");
  const quant = rows.find((r) => r.strategy_id === "quant_pmcc");
  return {
    strategy: "pmcc", kicker: window ? `Backtest · ${span(window.start, window.end)}` : "Backtest",
    symbol, figure: base ? moneySigned(base.pnl) : "—",
    detail: [base && `${pct(base.return_on_starting_nav)} baseline`,
             quant && `quant ${moneySigned(quant.pnl)}`].filter(Boolean).join(" · "),
    blurb: "A deep in-the-money call held as the stock, a short call sold against it each week.",
  };
}

/** Slow drifting light behind the page: decoration only, still when the system asks for less
 * motion (PO, LD-37). */
function Backdrop() {
  return (
    <div className="pm-home-bg" aria-hidden="true">
      <div className="pm-orb pm-orb-a" />
      <div className="pm-orb pm-orb-b" />
      <div className="pm-orb pm-orb-c" />
    </div>
  );
}

function Status({ live }: { live: Live | undefined }): ReactNode {
  const last = live?.runs.at(-1);
  if (!last) return null;
  return (
    <div className="pm-home-status">
      <span className="pm-live-dot" aria-hidden="true" />
      Last nightly run {timeET(last.run_at)}
    </div>
  );
}

export function Home() {
  const index = ready(useIndex());
  const live = ready(useLive());
  const thesis = useThesis();
  const headline = ready(useUniverseFile<Headline>("headline"));
  const symbol = index?.symbols[0]?.symbol;
  return (
    <main className="pm-home">
      <Backdrop />
      <header className="pm-hero">
        <div className="pm-hero-eyebrow">{symbol ?? "NVDA"} · options · LSEG data</div>
        <h1 className="pm-hero-title">
          Harvesting the <span className="pm-hero-glow">volatility risk premium.</span>
        </h1>
        <p className="pm-hero-lede">Systematic options strategies</p>
        <Status live={live} />
      </header>
      <div className="pm-tiles">
        <Tile {...thesisTile(thesis)} />
        <Tile {...liveTile(live, live?.symbol ?? symbol)} />
        <Tile {...wheelTile(live, symbol)} />
        <Tile {...pmccTile(headline, symbol, index?.window)} />
      </div>
    </main>
  );
}

// The home page, `#/` (UI-SPEC §6 › Home; PO, LD-36, LD-37): a headline over a tile per strategy,
// the live wheel first, on a slowly moving background. Each tile is a kicker, the strategy's
// name, one big figure from its own file, a line on what it does, and its pages. A modern break
// from the terminal look behind it (PO, LD-37): rounded, layered tiles, larger type, no panel
// chrome. From `live.json` (the live wheel, and the wheel backtest's result it carries) and
// `universe/headline.json` (the PMCC's).
import type { ReactNode } from "react";
import { useId } from "react";
import { Link } from "react-router-dom";

import { pageOf, pagePath, STRATEGIES, type StrategyKey } from "../app/pages";
import { shortDate } from "../components/charts/axis";
import { useIndex } from "../data/IndexContext";
import type { Loaded } from "../data/state";
import { useLive, useUniverseFile } from "../data/useRun";
import { moneySigned } from "../format/money";
import { orDash, pct, ratio } from "../format/number";
import { timeET } from "../format/time";
import type { Headline } from "../types/generated/headline";
import type { Live } from "../types/generated/live";
import { pickFor } from "./live/sections";

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
  detail: string;
  blurb: string;
  symbol: string | undefined;
  live?: boolean;
}

/** A strategy's tile: its name links to its first page, its pages are the chips below. */
function Tile({ strategy, kicker, figure, detail, blurb, symbol, live = false }: TileProps) {
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
      <div className="pm-tile-figure">{figure}</div>
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

/** The open order's option as LSEG picked it (LD-35), else as sent; or why there's none. */
function liveFigure(live: Live | undefined): string {
  if (!live) return "—";
  const [order] = live.orders;
  if (!order) return "No open order";
  const pick = pickFor(order, live.runs);
  return pick ? `$${pick.strike} ${pick.contract}` : `${order.strike ?? ""} ${order.contract}`;
}

function liveTile(live: Live | undefined, symbol: string | undefined): TileProps {
  const expiry = live?.orders[0]?.expiry;
  const detail = expiry ? `Open order · expires ${shortDate(expiry)}`
    : "The next order goes in for a week's first session";
  return { strategy: "live", kicker: "Live · nightly", figure: liveFigure(live), detail, symbol,
           live: true,
           blurb: `Sells one ${symbol ?? ""} option a week from a nightly GitHub Action; the `
             + "course's order system fills it." };
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
      Live · last run {timeET(last.run_at)}
    </div>
  );
}

export function Home() {
  const index = ready(useIndex());
  const live = ready(useLive());
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
        <Tile {...liveTile(live, live?.symbol ?? symbol)} />
        <Tile {...wheelTile(live, symbol)} />
        <Tile {...pmccTile(headline, symbol, index?.window)} />
      </div>
    </main>
  );
}

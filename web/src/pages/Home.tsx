// The home page, `#/` (UI-SPEC §6 › Home; PO, LD-36): what the site holds, then a card per
// strategy, the live wheel first and full width, the two backtests side by side under it. Each
// card says what the strategy does, where it stands, one headline from its own file, and links to
// its pages. From `live.json` (the live wheel, and the wheel backtest's result it carries) and
// `universe/headline.json` (the PMCC's).
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import { pageOf, pagePath, STRATEGIES, type StrategyKey } from "../app/pages";
import { Note } from "../components/Note";
import { PageFrame } from "../components/PageFrame";
import { useIndex } from "../data/IndexContext";
import type { Loaded } from "../data/state";
import { useLive, useUniverseFile } from "../data/useRun";
import { money, moneySigned } from "../format/money";
import { orDash, pct, ratio } from "../format/number";
import { timeET } from "../format/time";
import { W_FULL, W_HALF } from "../theme/tokens";
import type { Headline, HeadlineRow } from "../types/generated/headline";
import type { Live } from "../types/generated/live";
import { panel } from "./placeholder";

const OUTCOMES: Readonly<Record<string, string>> = {
  order: "an order",
  no_order: "no order",
  failed: "failed",
};

/** The value once loaded; nothing while loading or when the file is missing. */
function ready<T>(state: Loaded<T>): T | undefined {
  return state.kind === "ready" ? state.value : undefined;
}

/** A strategy's pages, as links in its menu's order. */
function PageLinks({ strategy, symbol }: { strategy: StrategyKey; symbol: string | undefined }) {
  const menu = STRATEGIES.find((s) => s.key === strategy)?.menu ?? [];
  return (
    <ul className="pm-home-links" aria-label="Pages">
      {menu.map((key) => {
        const page = pageOf(key);
        return <li key={key}><Link to={pagePath(page, symbol)}>{page.label}</Link></li>;
      })}
    </ul>
  );
}

function card(strategy: StrategyKey, width: typeof W_FULL | typeof W_HALF, note: string,
              body: ReactNode) {
  const label = STRATEGIES.find((s) => s.key === strategy)?.label ?? strategy;
  return { ...panel(strategy, label, width, body, false), note };
}

function LiveCard({ live, symbol }: { live: Live | undefined; symbol: string | undefined }) {
  const last = live?.runs.at(-1);
  return (
    <Note>
      <p>
        A GitHub Action runs each night after the close and sells one {symbol} option a week: a
        put near a 0.30 delta while it holds cash, covered calls if it&apos;s assigned. It writes
        the order to <code>open_orders.json</code> for Sanji, the course&apos;s order system, to
        fill. A second Action pulls {symbol}&apos;s volatility from LSEG for the page&apos;s
        charts.
      </p>
      {live && (
        <p>
          <b>Open orders:</b> {live.orders.length}.{" "}
          {last && <><b>Last run:</b> {timeET(last.run_at)},{" "}
            {OUTCOMES[last.outcome] ?? last.outcome} ({last.rule}).</>}
        </p>
      )}
      <PageLinks strategy="live" symbol={symbol} />
    </Note>
  );
}

function WheelCard({ live, symbol }: { live: Live | undefined; symbol: string | undefined }) {
  const b = live?.backtest;
  return (
    <Note>
      <p>
        The same wheel, backtested on {symbol}&apos;s hourly LSEG data
        {b ? ` from ${b.start} to ${b.end}` : ""}: a put each week, then covered calls once
        assigned. The review page tests whether it did what its thesis said.
      </p>
      {b && (
        <p>
          <b>Result:</b> {moneySigned(b.pnl)} ({pct(b.return_on_starting_cash)}) on{" "}
          {money(b.starting_cash)}, a Sharpe of {orDash(b.sharpe_annualized, ratio)}.
        </p>
      )}
      <PageLinks strategy="wheel" symbol={symbol} />
    </Note>
  );
}

function result(row: HeadlineRow | undefined): string {
  return row ? `${moneySigned(row.pnl)} (${pct(row.return_on_starting_nav)})` : "—";
}

function PmccCard({ headline, symbol, window }: {
  headline: Headline | undefined; symbol: string | undefined;
  window: { start: string; end: string } | undefined;
}) {
  const rows = headline?.rows.filter((r) => r.symbol === symbol) ?? [];
  const of = (id: string) => rows.find((r) => r.strategy_id === id);
  return (
    <Note>
      <p>
        A poor man&apos;s covered call on {symbol}
        {window ? `, ${window.start} to ${window.end}` : ""}: a deep in-the-money call held as a
        stand-in for the stock, a short call sold against it each week. A quant variant, with
        gates that skip poorly paid weeks, against a fixed-delta baseline.
      </p>
      {rows.length > 0 && (
        <p>
          <b>Result:</b> baseline {result(of("baseline_pmcc"))}; quant {result(of("quant_pmcc"))}.
        </p>
      )}
      <PageLinks strategy="pmcc" symbol={symbol} />
    </Note>
  );
}

export function Home() {
  const index = ready(useIndex());
  const live = ready(useLive());
  const headline = ready(useUniverseFile<Headline>("headline"));
  const symbol = index?.symbols[0]?.symbol;
  return (
    <PageFrame panels={[
      { ...panel("about", "What's here", W_FULL, (
          <Note>
            <p>
              Options strategies built on LSEG market data: a wheel that trades live each night
              through the course&apos;s order system, and the two backtests behind it. Each card below links to its strategy&apos;s pages, as do the menus above.
            </p>
          </Note>), false) },
      card("live", W_FULL, "live, nightly",
           <LiveCard live={live} symbol={live?.symbol ?? symbol} />),
      card("wheel", W_HALF, "backtest, hourly", <WheelCard live={live} symbol={symbol} />),
      card("pmcc", W_HALF, "backtest, hourly",
           <PmccCard headline={headline} symbol={symbol} window={index?.window} />),
    ]} />
  );
}

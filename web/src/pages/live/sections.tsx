// The live page's panels (L4-01; UI-SPEC §6 › Live): the algorithm in words, the open orders
// with the strike LSEG gave each (PO, LD-35), Sanji's positions and fills as he writes them, the
// nightly run log with each pick's quote at the close (PO, LD-15), and the rules. Every value is
// read from `live.json`.
import { Link } from "react-router-dom";

import { DataTable, type TableColumn } from "../../components/DataTable";
import { Empty, Note } from "../../components/Note";
import { money, moneySigned, price } from "../../format/money";
import { iv, orDash, pct, ratio, spreadPct } from "../../format/number";
import { timeET } from "../../format/time";
import { stateLabel } from "../../format/wheel";
import type {
  Live,
  LiveOrder,
  LivePick,
  LiveRuleOut,
  LiveRun,
  SanjiFileOut,
} from "../../types/generated/live";

/** A strike token's value, so strikes sort by value, not as text: a number (`155`), or a
 * percent's (`pct:-5` is −5, LD-29); a token without one (`atm`) sorts last. */
export function strikeValue(strike: string | null | undefined): number | undefined {
  if (strike === null || strike === undefined) return undefined;
  const value = Number(strike.startsWith("pct:") ? strike.slice(4) : strike);
  return Number.isFinite(value) ? value : undefined;
}

// ---- the algorithm ------------------------------------------------------------------------------

/** What the wheel does each week, why it was chosen, from the backtest's numbers. */
export function Algorithm({ live }: { live: Live }) {
  const b = live.backtest;
  return (
    <Note>
      <p>
        Each week the live wheel sells one option on {live.symbol}, one contract at a time, and
        writes it to <code>open_orders.json</code> for Sanji, the course&apos;s order system, to
        fill. While it holds only cash, it sells a <b>put</b> for the week&apos;s first trading
        session. From the close the night before, it finds the out-of-the-money put expiring that
        week whose delta is nearest −0.30, and sends its strike as a distance below the close in
        percent: Sanji sets the strike that far below the open, so a gap overnight moves it with
        the stock. The limit is the put&apos;s mid at the open, and it&apos;s sold only if the
        cash covers the strike picked at the close × 100, with room for a gap at the open. If the
        put expires worthless, it keeps the premium and sells another the next week. If
        it&apos;s assigned, it holds 100 shares and sells a <b>covered call</b> each week instead,
        never below what the shares cost, until they&apos;re called away and it holds cash again.
      </p>
      {b && (
        <p>
          <b>Why the wheel:</b> it&apos;s the strategy already built and backtested here. On{" "}
          {live.symbol} from {b.start} to {b.end}, it made {moneySigned(b.pnl)} (
          {pct(b.return_on_starting_cash)}) on {money(b.starting_cash)}, with an annualized Sharpe
          of {orDash(b.sharpe_annualized, ratio)} against the baseline PMCC&apos;s{" "}
          {orDash(b.baseline_sharpe_annualized, ratio)} over the same weeks. It also suits Sanji,
          which settles expiries and assignments itself, so the algorithm only has to sell one
          option at the start of each week.{" "}
          <Link to={`/wheel-review/${live.symbol}`}>The wheel&apos;s backtest review</Link> has
          the rest.
        </p>
      )}
      <p>
        Earnings weeks are traded like any other, as in the backtest, which had no event filter:
        the premium is richer and assignment likelier. The first week traded, to Nov 20, likely
        spans {live.symbol}&apos;s earnings.
      </p>
      <p>The rules, each with the ID the run log names, are the last panel on the page.</p>
    </Note>
  );
}

const RULE_COLUMNS: readonly TableColumn<LiveRuleOut>[] = [
  { id: "id", header: "ID", sort: (r) => r.id, cell: (r) => r.id },
  { id: "rule", header: "Rule", sort: (r) => r.rule, cell: (r) => r.rule },
  { id: "words", header: "What it does", sort: (r) => r.words, cell: (r) => r.words },
];

/** The rules, each in its words with its ID, as `configs/live.yaml` holds them. */
export function LiveRules({ live }: { live: Live }) {
  return (
    <DataTable label="Live wheel rules" rows={live.rules} columns={RULE_COLUMNS}
               rowId={(r) => r.id} wrap grow />
  );
}

// ---- open orders ----------------------------------------------------------------------------

const ACTIONS: Readonly<Record<string, string>> = {
  BUY: "Buy",
  SEL: "Sell",
  SHT: "Sell to open",
  BTC: "Buy to close",
};

function limit(o: LiveOrder): string {
  return o.order_type === "mkt" ? "Market" : `Limit, ${o.lmt_prc ?? "—"}`;
}

/** An open order with the option the nightly run picked for it from LSEG (PO, LD-35). */
type OrderRow = LiveOrder & { picked: LivePick | null };

/** The pick an order was sent for: the latest run-log row that ordered, for the order's session,
 * the same contract and expiry. Matched by those, not the id, since Monday Nov 16's order was
 * re-sent under a new id (LD-29). None when no row matches. */
export function pickFor(order: LiveOrder, runs: readonly LiveRun[]): LivePick | null {
  const row = runs.findLast((r) => r.outcome === "order" && r.next_session === order.for
    && r.pick?.contract === order.contract && r.pick.expiry === order.expiry);
  return row?.pick ?? null;
}

/** `$155, delta −0.32`. */
function picked(p: LivePick | null): string {
  return p === null ? "—" : `$${p.strike}, delta ${ratio(p.delta)}`;
}

const ORDER_COLUMNS: readonly TableColumn<OrderRow>[] = [
  { id: "id", header: "ID", sort: (o) => o.id, cell: (o) => o.id },
  { id: "for", header: "For", sort: (o) => o.for, cell: (o) => o.for },
  { id: "action", header: "Action", sort: (o) => o.action,
    cell: (o) => `${ACTIONS[o.action] ?? o.action} (${o.action})` },
  { id: "qty", header: "Qty", num: true, sort: (o) => o.qty, cell: (o) => String(o.qty) },
  { id: "contract", header: "Contract", sort: (o) => o.contract, cell: (o) => o.contract },
  { id: "expiry", header: "Expiry", sort: (o) => o.expiry ?? undefined,
    cell: (o) => o.expiry ?? "—" },
  { id: "picked", header: "Picked at the close", num: true,
    sort: (o) => strikeValue(o.picked?.strike), cell: (o) => picked(o.picked) },
  { id: "strike", header: "Sent as", num: true, sort: (o) => strikeValue(o.strike),
    cell: (o) => o.strike ?? "—" },
  { id: "limit", header: "Limit", sort: limit, cell: limit },
  { id: "ref", header: "Ref", sort: (o) => o.ref ?? undefined, cell: (o) => o.ref ?? "—" },
];

/** The open orders, each with the strike LSEG gave the run beside the token Sanji gets. */
export function OpenOrders({ live }: { live: Live }) {
  if (live.orders.length === 0) return <Empty>No open orders tonight.</Empty>;
  const rows = live.orders.map((o) => ({ ...o, picked: pickFor(o, live.runs) }));
  return <DataTable label="Open orders" rows={rows} columns={ORDER_COLUMNS}
                    rowId={(o) => o.id} grow />;
}

// ---- Sanji's files ------------------------------------------------------------------------------

/** One of Sanji's files, its text exactly as he wrote it: its format is unknown until he
 * resolves an order (L5-01). */
export function SanjiFile({ file, empty }: { file: SanjiFileOut | null; empty: string }) {
  if (file === null) return <Empty>{empty}</Empty>;
  return <pre className="pm-file" aria-label={file.path}>{file.text}</pre>;
}

// ---- the run log --------------------------------------------------------------------------------

const OUTCOMES: Readonly<Record<string, string>> = {
  order: "Order",
  no_order: "No order",
  failed: "Failed",
};

/** `$155 put, 2026-11-20`. */
export function option(p: LivePick): string {
  return `$${p.strike} ${p.contract}, ${p.expiry}`;
}

function quote(p: LivePick | null, value: (p: LivePick) => number | null,
               format: (v: number) => string): string {
  return p === null ? "" : orDash(value(p), format);
}

const RUN_COLUMNS: readonly TableColumn<LiveRun>[] = [
  { id: "run", header: "Run (ET)", sort: (r) => r.run_at, cell: (r) => timeET(r.run_at) },
  { id: "next", header: "Planning", sort: (r) => r.next_session, cell: (r) => r.next_session },
  { id: "state", header: "State", sort: (r) => r.state ?? undefined,
    cell: (r) => orDash(r.state, stateLabel) },
  { id: "cash", header: "Cash", num: true, sort: (r) => r.cash ?? undefined,
    cell: (r) => orDash(r.cash, money) },
  { id: "outcome", header: "Outcome", sort: (r) => r.outcome,
    cell: (r) => <span className={r.outcome === "failed" ? "pm-down" : undefined}>
      {OUTCOMES[r.outcome] ?? r.outcome}</span> },
  { id: "rule", header: "Rule", sort: (r) => r.rule,
    cell: (r) => r.rule },
  { id: "why", header: "Why", sort: (r) => r.reason, cell: (r) => r.reason },
  { id: "option", header: "Picked at the close", sort: (r) => strikeValue(r.pick?.strike),
    cell: (r) => (r.pick ? option(r.pick) : "") },
  { id: "sent", header: "Sent as", sort: (r) => strikeValue(r.strike_sent),
    cell: (r) => r.strike_sent ?? (r.order_id ? "—" : "") },
  { id: "delta", header: "Delta", num: true, sort: (r) => r.pick?.delta,
    cell: (r) => quote(r.pick, (p) => p.delta, ratio) },
  { id: "iv", header: "IV", num: true, sort: (r) => r.pick?.iv,
    cell: (r) => quote(r.pick, (p) => p.iv, iv) },
  { id: "bid", header: "Bid", num: true, sort: (r) => r.pick?.bid ?? undefined,
    cell: (r) => quote(r.pick, (p) => p.bid, price) },
  { id: "ask", header: "Ask", num: true, sort: (r) => r.pick?.ask ?? undefined,
    cell: (r) => quote(r.pick, (p) => p.ask, price) },
  { id: "mid", header: "Mid", num: true, sort: (r) => r.pick?.mid ?? undefined,
    cell: (r) => quote(r.pick, (p) => p.mid, price) },
  { id: "spread", header: "Spread", num: true, sort: (r) => r.pick?.spread ?? undefined,
    cell: (r) => quote(r.pick, (p) => p.spread, spreadPct) },
];

/** The run log, newest first. */
export function RunLog({ live }: { live: Live }) {
  if (live.runs.length === 0) return <Empty>No nightly run yet.</Empty>;
  return (
    <DataTable label="Nightly run log" rows={[...live.runs].reverse()} columns={RUN_COLUMNS}
               rowId={(r) => r.run_at} grow />
  );
}

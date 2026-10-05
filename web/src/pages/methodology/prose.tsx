// The methodology page's prose panels (UI-SPEC §6.4): the data and RIC scheme, bar timing and the
// look-ahead guard, the fill model, the Reg T treatment with its exact citations (DEC-10), and
// the limits of this backtest (DEC-109). Every figure in them is read from the results as the
// page renders, and a claim is made only where the results bear it out; rules are named, never
// by ID (PO, DEC-113).
import type { ReactNode } from "react";

import { KeyValue, RuleLink } from "../../components/cells";
import { shortDate } from "../../components/charts/axis";
import { Note } from "../../components/Note";
import { money, moneySigned } from "../../format/money";
import { count, meanCI, ratio } from "../../format/number";
import type { Robustness } from "../../types/generated/robustness";
import type { Rules } from "../../types/generated/rules";
import type { InstrumentOut, RunResult } from "../../types/generated/run_result";
import { legSplit, longRode } from "../compare/figures";
import { assignments, longestLong, longSelectorAblation, longTrips, overlap } from "./figures";

/** A rule's name as the runs' configs have it, else its ID's link alone. */
export type RuleName = (id: string) => string;

export function ruleNames(runs: readonly RunResult[]): RuleName {
  const rules = runs.flatMap((r) => r.config.strategy.rules);
  return (id) => rules.find((r) => r.id === id)?.name ?? "rule";
}

function Named({ id, name, lower = true }: { id: string; name: RuleName; lower?: boolean }) {
  const text = name(id);
  return <RuleLink id={id} prose>{lower ? text.toLowerCase() : text}</RuleLink>;
}

// ---- data and RIC scheme -----------------------------------------------------------------------

export function DataScheme({ example }: { example: InstrumentOut | undefined }) {
  return (
    <Note>
      <p>
        <b>Data.</b> Every price is an LSEG hourly bar: the stock&apos;s open, high, low, close
        and trades, and each option&apos;s BID and ASK, with its last trade (TRDPRC_1) on a bar
        it traded. Stock and options share the bar size. The data are fetched once, on the
        author&apos;s machine, and cached; no backtest, build or page of this site calls LSEG.
      </p>
      <p>
        <b>RICs.</b> An option is asked for as{" "}
        <code>{"{ROOT}{MONTH}{DAY}{YY}{STRIKE}.U"}</code>, plus <code>{"^{MONTH}{YY}"}</code> once
        it has expired. The month letter carries the right as well (calls A to L, puts M to X),
        and the caret takes the call letter even for a put; the day is two digits and the strike
        × 100 five.
        {example?.occ && <> The first long bought here, <code>{example.ric}</code>, is the
          OCC&apos;s <code className="pm-occ">{example.occ}</code>.</>}{" "}
        For a few days after expiry a contract still answers only to its live form, so an expired
        one is asked with the caret first, then without it.
      </p>
      <p>
        <b>Guess and check.</b> Each week&apos;s expiry is its last session on the stock tape, so
        a holiday week never gets an invented Friday, and the long legs&apos; monthlies are third
        Fridays. Strikes are guessed on each symbol&apos;s probed increment, across the
        window&apos;s range; a RIC LSEG doesn&apos;t know comes back empty and is logged, never a
        crash, and Data coverage counts it.
      </p>
      <p>
        <b>Cache and manifest.</b> Each fetch unit (the stock tape, an expiry&apos;s calls or
        puts) is a parquet file with a sidecar, listed in a manifest with its RIC, row count and
        hash, and never fetched over. Every result records that manifest&apos;s hash with the git
        commit and the config and lockfile hashes; the footer shows them.
      </p>
    </Note>
  );
}

// ---- bar timing and the look-ahead guard -------------------------------------------------------

export function BarTiming({ name }: { name: RuleName }) {
  return (
    <Note>
      <p>
        <b>Bars are keyed by their end.</b> LSEG stamps an hourly bar at its start, but its BID
        and ASK are the quotes at its end, as checked on a known contract before anything was
        built. Acting on them at the stamp would be look-ahead, so every bar is keyed by its end
        time, and every decision is made at a bar&apos;s end and filled at that bar&apos;s mid.
      </p>
      <p>
        <b>Look-ahead is impossible by construction.</b> A strategy never sees a data table. On
        each bar the engine hands it a MarketView, which returns only data stamped at or before
        the decision time and raises an error on any request for later data. Strikes are fetched
        across the whole window&apos;s range, but a rule chooses among them only through
        MarketView.
      </p>
      <p>
        <b>The close.</b> A session&apos;s close is its last bar&apos;s last trade, not the
        official closing auction, which the cache doesn&apos;t hold. The two differed by up to
        0.09% in the probes, so a short pinned at its strike can be in the money by one and out
        of it by the other. The <Named id="X-S3" name={name} /> uses the last bar ending by
        15:00 ET on the week&apos;s final session.
      </p>
    </Note>
  );
}

// ---- fill model --------------------------------------------------------------------------------

export function FillModel({ rules }: { rules: Rules | null }) {
  const strategies = rules?.strategies.filter((s) => s.family === "strategy") ?? [];
  const friction = [...new Set(rules?.strategies
    .filter((s) => s.family === "friction").map((s) => s.spread_capture) ?? [])].sort();
  const captures = [...new Set(strategies.map((s) => s.spread_capture))];
  const fees = [...new Set(strategies.map((s) => s.fee_per_contract))];
  return (
    <div className="pm-stack">
      <Note>
        <p>
          Every order is a limit at the decision bar&apos;s mid, (BID + ASK) ÷ 2, and fills there,
          on that bar. A bar without a BID or an ASK fills nothing: no print is ever invented, and
          a stale mark, carried only to value a position, never fills. Friction moves a fill off
          the mid by a share of the half-spread, <code>spread_capture</code>: a buy fills at mid +
          capture × half-spread, a sell at mid − it. Friction ([4]) runs both strategies at each
          capture against themselves at the mid.
        </p>
      </Note>
      {rules && (
        <KeyValue
          label="Fill model"
          rows={[
            ["Fill price", "the decision bar's mid, at its end"],
            ["No BID or no ASK", "no fill"],
            ["Spread capture, both strategies", captures.map((c) => ratio(c)).join(", ") || "—"],
            ["Spread capture, the friction runs",
             friction.map((c) => ratio(c)).join(", ") || "none"],
            ["Fee per contract", fees.map(money).join(", ") || "—"],
          ]}
        />
      )}
    </div>
  );
}

// ---- Reg T treatment ---------------------------------------------------------------------------

function Quote({ cite, children }: { cite: string; children: ReactNode }) {
  return (
    <blockquote className="pm-quote">
      <p>{children}</p>
      <cite>{cite}</cite>
    </blockquote>
  );
}

// The day the quotes below were read from eCFR (12 CFR 220.12, unchanged since 1998) and
// finra.org (Rule 4210, last amended by SR-FINRA-2025-017, effective June 4 2026): DEC-10.
const READ_ON = "2026-10-04";

/** The shortest span of nine calendar months, in days (June 1 to March 1). */
const NINE_MONTHS_DAYS = 273;

/** Whether every long bought was within nine months, from the blotters. */
function Longest({ runs }: { runs: readonly RunResult[] | null }) {
  const longest = runs ? longestLong(runs) : undefined;
  if (longest === undefined) return null;
  return (
    <>, and the longest any long here had left when bought was {count(longest)} days
      {longest <= NINE_MONTHS_DAYS ? ", so every long was paid in full" : ", past nine months"}</>
  );
}

/** Whether a short-stock requirement ever applied: the missed assignments over both runs. */
function Assigned({ runs, symbol }: { runs: readonly RunResult[] | null; symbol: string }) {
  if (!runs) return null;
  const n = assignments(runs);
  return n === 0
    ? <> On {symbol} no short was ever assigned, so neither short-stock requirement applied.</>
    : <> On {symbol} shorts were assigned {count(n)} times over both strategies; each
        strategy&apos;s ledger carries the requirement.</>;
}

// FINRA 4210(b)(4)'s minimum equity for a margin account.
const MIN_EQUITY = 2000;

function MinimumEquity({ cash }: { cash: number }) {
  return cash >= MIN_EQUITY
    ? <>, which the starting cash of {money(cash)} clears</>
    : <>, above the starting cash of {money(cash)}</>;
}

export function RegTTreatment({ runs, symbol, startingCash, name }: {
  runs: readonly RunResult[] | null;
  symbol: string;
  startingCash: number | undefined;
  name: RuleName;
}) {
  return (
    <Note>
      <p>
        Each strategy&apos;s account is held to the minimums of Regulation T and FINRA Rule 4210
        for a margin account. The rules are quoted as read on {READ_ON}: 12 CFR 220.12 from the
        eCFR, unchanged since 1998, and Rule 4210 from finra.org, last amended effective June 4
        2026.
      </p>
      <p>
        <b>The long call is paid in full.</b> Regulation T&apos;s 50% requirement leaves out
        &ldquo;a long position in an option&rdquo; (12 CFR 220.12(a)), and leaves a listed option
        to &ldquo;the rules of the registered national securities exchange or the registered
        securities association authorized to trade the option&rdquo; (220.12(f)(1)). FINRA:
      </p>
      <Quote cite="FINRA Rule 4210(f)(2)(D)">
        In the case of any put, call, currency warrant, currency index warrant, or stock index
        warrant carried &ldquo;long&rdquo; in a customer&apos;s account that expires in nine months
        or less, initial margin must be deposited and maintained equal to at least 100 percent of
        the purchase price of the option or warrant.
      </Quote>
      <p>
        Neither rule states nine months in days; the shortest nine calendar months run{" "}
        {NINE_MONTHS_DAYS} days<Longest runs={runs} />.
      </p>
      <p>
        <b>The covered short call needs nothing.</b> The{" "}
        <Named id="E-S5" name={name} /> keeps the long&apos;s strike at or below the short&apos;s,
        and the long always expires after it, so the two are a spread, whose last condition is
        that &ldquo;the &lsquo;short&rsquo; option(s) must expire on or before the expiration date
        of the &lsquo;long&rsquo; option(s)&rdquo; (4210(f)(2)(A)(xxxii)e). For a spread:
      </p>
      <Quote cite="FINRA Rule 4210(f)(2)(H)(i)">
        the margin required on the &ldquo;short&rdquo; options shall be the lesser of: a. The
        margin required pursuant to paragraph (f)(2)(E); or b. The maximum potential loss. [&hellip;]
        &ldquo;Long&rdquo; options must be paid for in full. The proceeds of the
        &ldquo;short&rdquo; options may be applied towards the cost of the &ldquo;long&rdquo;
        options and/or any margin requirement.
      </Quote>
      <p>
        With the long&apos;s strike at or below the short&apos;s, the maximum potential loss is
        $0, so the short adds no requirement, and an uncovered short would be an engine error,
        not a margin case.
      </p>
      <p>
        <b>Short stock after a missed assignment.</b> If a short call is assigned (the{" "}
        <Named id="X-S5" name={name} />), the shares are sold short at its strike while the long
        call is still held. Regulation T then asks the proceeds alone, no additional 50%:
      </p>
      <Quote cite="12 CFR 220.12(c)(2)">
        100 percent of the current market value if a security exchangeable or convertible within
        90 calendar days without restriction other than the payment of money into the security
        sold short is held in the account, provided that any long call to be used as margin in
        connection with a short sale of the underlying security is an American-style option
        issued by a registered clearing corporation and listed or traded on a registered national
        securities exchange with an exercise price that does not exceed the price at which the
        underlying security was sold short.
      </Quote>
      <Quote cite="FINRA Rule 4210(f)(2)(H)(v)a">
        When a component underlying an option or warrant is carried &ldquo;long&rdquo;
        (&ldquo;short&rdquo;) in the same account as a &ldquo;long&rdquo; put (call) or warrant
        specifying equivalent units of the underlying component, the minimum amount of margin that
        must be maintained on the underlying component is 10 percent of the aggregate
        option/warrant exercise price plus the &ldquo;out-of-the-money&rdquo; amount, not to exceed
        the minimum maintenance required pursuant to paragraph (c) of this Rule.
      </Quote>
      <p>
        Without the long, plain short stock: &ldquo;150 percent of the current market value of the
        security&rdquo; initially (220.12(c)(1)), and &ldquo;$5.00 per share or 30 percent of the
        current market value, whichever amount is greater, of each stock &lsquo;short&rsquo; in the
        account selling at $5.00 per share or above&rdquo; to maintain (4210(c)(3)). A requirement
        that isn&apos;t a whole $0.0001 is rounded up.<Assigned runs={runs} symbol={symbol} />
      </p>
      <p>
        <b>Not modelled.</b> A broker may ask more: FINRA has its members &ldquo;formulate their
        own margin requirements&rdquo; (4210(d)(1)(B)). A margin account needs &ldquo;equity of at
        least $2,000&rdquo; (4210(b)(4)){startingCash !== undefined
          && <MinimumEquity cash={startingCash} />}.
        FINRA&apos;s intraday margin rule (4210(d)(2)) isn&apos;t modelled. Available funds are
        NAV less initial margin; a bar below zero is flagged, and the strategy page then says the
        position couldn&apos;t have been held in a real Reg T account.
      </p>
    </Note>
  );
}

// ---- the limits of this backtest ---------------------------------------------------------------

export interface LimitsInput {
  /** Quant's full run, then the baseline's. */
  runs: readonly [RunResult, RunResult];
  robustness: Robustness | null;
  rules: Rules | null;
  symbols: readonly string[];
}

function plural(n: number, one: string, many: string): string {
  return `${count(n)} ${n === 1 ? one : many}`;
}

function OneWindow({ runs, symbols }: LimitsInput) {
  const [quant] = runs;
  const weeks = quant.summary.cycle_stats?.weeks;
  const { start, end } = quant.config.window;
  const splits = runs.flatMap((r) => legSplit(r) ?? []);
  const rose = splits.length > 0 && splits.every((s) => s.intrinsic > 0);
  return (
    <p>
      <b>{symbols.length === 1 ? "One symbol, one window." : "One window."}</b> These results are{" "}
      {plural(symbols.length, "symbol", "symbols")} ({symbols.join(", ")})
      {weeks !== undefined && <> over {plural(weeks, "week", "weeks")}</>}, {start} to {end}
      {rose && <>, a window in which the stock rose under every long</>}. A PMCC is net long
      delta: the long call gains with the stock, while each week&apos;s short caps that
      week&apos;s gain and loses when the stock runs through its strike. A rally rewards the
      long and runs over the shorts.
    </p>
  );
}

function Legs({ runs }: LimitsInput) {
  const splits = runs.flatMap((r) => legSplit(r) ?? []);
  if (splits.length === 0) return null;
  const leg = (r: RunResult) => r.attribution?.leg;
  return (
    <p>
      <b>The long made the result.</b>{" "}
      {runs.map((r, i) => {
        const s = legSplit(r);
        const l = leg(r);
        if (!s || !l) return null;
        return (
          <span key={r.manifest.run_id}>
            {i > 0 && " "}{s.name}&apos;s long leg made {moneySigned(s.long)} (
            {moneySigned(l.long_intrinsic)} intrinsic, {moneySigned(l.long_extrinsic)} extrinsic),
            its shorts {moneySigned(s.shorts)}, for a P&amp;L of {moneySigned(s.pnl)}.
          </span>
        );
      })}
      {splits.every(longRode) && <> In each, the long made more than the whole P&amp;L.</>}
    </p>
  );
}

function Timing({ runs, robustness, rules, name }: LimitsInput & { name: RuleName }) {
  const [quant, baseline] = runs;
  const firsts = runs.flatMap((r) => {
    const first = longTrips(r)[0];
    return first?.closed ? [{ run: r, first, closed: first.closed }] : [];
  });
  const q = legSplit(quant);
  const b = legSplit(baseline);
  const a = rules && robustness ? longSelectorAblation(rules, robustness) : undefined;
  return (
    <p>
      <b>Rolls book the gain; they don&apos;t make it.</b>{" "}
      {firsts.map(({ run, first, closed }, i) => (
        <span key={run.manifest.run_id}>
          {i > 0 && " "}{run.config.strategy.name}&apos;s first long made{" "}
          {moneySigned(first.pnl)}, sold {shortDate(closed.time.slice(0, 10))} at the{" "}
          <Named id={closed.ruleId} name={name} />.
        </span>
      ))}
      {q && b && a && q.long > b.long && (
        <> {q.name}&apos;s long leg made {moneySigned(q.long - b.long)} more than{" "}
          {b.name}&apos;s, but {a.label} made {money(Math.abs(a.pnl_vs_reference))}{" "}
          {a.pnl_vs_reference >= 0 ? "more" : "less"} than {q.name}
          {a.pnl_vs_reference >= 0
            ? <>, so its long selection isn&apos;t shown to help: its better long is mostly when
                its roll fell.</>
            : "."}</>
      )}
    </p>
  );
}

function Noise({ runs }: LimitsInput) {
  const [quant, baseline] = runs;
  const qc = quant.summary.metrics?.weekly_return;
  const bc = baseline.summary.metrics?.weekly_return;
  if (!qc || !bc) return null;
  const apart = !overlap(qc, bc);
  return (
    <p>
      <b>{apart ? "The two can be told apart." : "The two can't be told apart."}</b> Mean weekly
      return: {quant.config.strategy.name} {meanCI(qc)}, {baseline.config.strategy.name}{" "}
      {meanCI(bc)}, 95% CIs over {plural(qc.weeks, "week", "weeks")} that{" "}
      {apart ? "don't overlap" : "overlap"}.
    </p>
  );
}

export function Limits(input: LimitsInput) {
  const name = ruleNames(input.runs);
  const reset = input.runs[0].config.strategy.rules.find((r) => r.id === "X-L1");
  const delta = reset?.params.min_delta;
  return (
    <Note>
      <OneWindow {...input} />
      <Legs {...input} />
      <Timing {...input} name={name} />
      <Noise {...input} />
      <p>
        <b>Other markets.</b> In a flat or mean-reverting market the shorts would become the
        income, while the long still loses its extrinsic value to time. In a falling one the long
        loses intrinsic value too, and the <Named id="X-L1" name={name} /> sells it at a loss
        {typeof delta === "number" && <> once its delta drops below {ratio(delta)}</>}. Either
        would likely change these results, and this window can&apos;t say by how much.
      </p>
      <p>
        <b>No bear market.</b> LSEG&apos;s hourly option history reaches back only about a year,
        to late October 2025, so no bear market like 2022&apos;s can be tested with these data.
      </p>
    </Note>
  );
}

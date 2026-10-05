// The methodology page's prose panels (UI-SPEC §6.4): the limits of this backtest (DEC-109), bar
// timing and the look-ahead guard, and the fill model. Every figure in them is read from the results as the
// page renders, and a claim is made only where the results bear it out; rules are named, never
// by ID (PO, DEC-113).
import { KeyValue, RuleLink } from "../../components/cells";
import { shortDate } from "../../components/charts/axis";
import { Note } from "../../components/Note";
import { money, moneySigned } from "../../format/money";
import { count, meanCI, ratio } from "../../format/number";
import type { Robustness } from "../../types/generated/robustness";
import type { Rules } from "../../types/generated/rules";
import type { RunResult } from "../../types/generated/run_result";
import { legSplit, longRode } from "../compare/figures";
import { longSelectorAblation, longTrips, overlap } from "./figures";

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
          capture × half-spread, a sell at mid − it. The Friction table runs both strategies at
          each capture against themselves at the mid.
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

// The wheel review page (UI-SPEC §6; PO, WD-22): whether the wheel did what its thesis said.
// Readouts, then the thesis and each claim's verdict, the benchmark table, the fill model with the
// mid-vs-print evidence for the puts and the calls, the friction runs, and the rules from the
// config. Arriving at `#/wheel-review/:symbol/<ID>` (every wheel rule link) scrolls to that rule.
import type { ReactNode } from "react";
import { useParams } from "react-router-dom";

import { WHEEL_RUN } from "../app/pages";
import type { Readout } from "../components/Readouts";
import { pending, PageFrame } from "../components/PageFrame";
import { Empty } from "../components/Note";
import type { Loaded } from "../data/state";
import { useWheelRuns } from "../data/useRun";
import { moneySigned } from "../format/money";
import { count, orDash, pct, ratio } from "../format/number";
import { W_FULL, W_HALF } from "../theme/tokens";
import type { WheelResult } from "../types/generated/wheel_result";
import { panel, whenLoaded } from "./placeholder";
import {
  benchmarkCaption,
  Benchmarks,
  FillModel,
  Friction,
  Thesis,
  Verdicts,
  WheelMidVsPrint,
  WheelRules,
  wheelScatterCaption,
} from "./wheel/review";

const READOUT_HINTS = [
  ["Claims met", "The thesis's claims the results bear out"],
  ["P&L", "Ending NAV − starting cash; claim 1 is P&L > $0"],
  ["Return on starting cash", "Not annualized; claim 3 is a return above the S&P 500's"],
  ["Sharpe (annualized)", "Claim 2 is a Sharpe above the baseline PMCC's"],
  ["Prints inside the quote", "Prints of the options sold at or between the bid and the ask"],
] as const;

function readouts(run: WheelResult): Readout[] {
  const { thesis, metrics: m, benchmarks: b } = run.summary;
  const e = run.fill_evidence;
  const shown: readonly (readonly [string, string])[] = [
    [`${count(thesis.filter((v) => v.met).length)} of ${count(thesis.length)}`, ""],
    [moneySigned(m.pnl), ""],
    [pct(m.return_on_starting_cash), `; the S&P 500's: ${pct(b.sp500.price_return)}`],
    [orDash(m.sharpe_annualized, ratio),
     `; the baseline PMCC's: ${orDash(b.baseline_pmcc.sharpe_annualized, ratio)}`],
    [orDash(e.within_spread, pct), `; of ${count(e.fit?.n ?? 0)} prints`],
  ];
  return READOUT_HINTS.map(([label, hint], i) => {
    const [value, extra] = shown[i] ?? ["—", ""];
    return { label, value, hint: `${hint}${extra}` };
  });
}

/** The wheel's own run among a symbol's wheel runs. */
function reference(runs: readonly WheelResult[]): WheelResult | undefined {
  return runs.find((r) => r.manifest.run_id === WHEEL_RUN);
}

/** A panel body over the wheel's own run, or its in-panel state. */
function withWheel(state: Loaded<WheelResult[]>, render: (run: WheelResult) => ReactNode) {
  return whenLoaded(state, (runs) => {
    const run = reference(runs);
    return run ? render(run) : <Empty>No results for the wheel&apos;s own run.</Empty>;
  });
}

export function WheelReview() {
  const { symbol = "", ruleId } = useParams();
  const state = useWheelRuns(symbol);
  const run = state.kind === "ready" ? reference(state.value) : undefined;
  const body = (render: (run: WheelResult) => ReactNode) => withWheel(state, render);
  const group = (name: string) => (r: WheelResult) => r.fill_evidence.groups.find(
    (g) => g.group === name);
  return (
    <PageFrame
      readouts={run ? readouts(run) : pending(READOUT_HINTS.map(([l, h]) => [l, h]))}
      panels={[
        panel("thesis", "Thesis", W_FULL, body((r) => <Thesis run={r} />), false),
        { ...panel("verdicts", "Verdicts", W_FULL, body((r) => <Verdicts run={r} />)),
          note: "met when the wheel's number is higher",
          caption: <>Claim 1 compares the P&amp;L with $0, the shares still held at the end
            marked at their mid; claim 2 the annualized Sharpe with the baseline PMCC&apos;s;
            claim 3 the return on starting cash with the S&amp;P 500&apos;s price return. A
            claim missing a number is not met.</> },
        { ...panel("benchmarks", "Benchmarks", W_FULL, body((r) => <Benchmarks run={r} />)),
          note: "the same symbol, window and r",
          ...(run ? { caption: benchmarkCaption(run) } : {}) },
        panel("fills", "Fill model", W_FULL, body((r) => <FillModel run={r} />), false),
        { ...panel("puts", "Mid vs print — puts", W_HALF, body((r) => (
            <WheelMidVsPrint run={r} group={group("puts")(r)} label="Mid vs print — puts" />))),
          note: "every pair", caption: wheelScatterCaption("put sold") },
        { ...panel("calls", "Mid vs print — calls", W_HALF, body((r) => (
            <WheelMidVsPrint run={r} group={group("calls")(r)} label="Mid vs print — calls" />))),
          note: "every pair", caption: wheelScatterCaption("call sold") },
        { ...panel("friction", "Friction runs", W_FULL, whenLoaded(state, (runs) => {
            const r = reference(runs);
            return r ? <Friction runs={runs} reference={r} />
              : <Empty>No results for the wheel&apos;s own run.</Empty>;
          })),
          note: "the same trades, paying part of the spread",
          caption: <>Each run is the wheel with its fills moved from the mid by the spread capture
            × half the spread: a sale at mid − capture × half-spread. The trades, the rules and
            the data are the same; only the fills change.</> },
        { ...panel("rules", "Rules", W_FULL, body((r) => <WheelRules run={r} target={ruleId} />)),
          note: "rendered from the config the wheel ran with",
          caption: <>Each week the wheel sells one option: a put while it holds only cash, a call
            while it holds the shares. Each is held to expiry, then expires or is assigned. ▸
            opens a rule&apos;s reasoning; hover a row for the rule stated exactly.</> },
      ]}
    />
  );
}

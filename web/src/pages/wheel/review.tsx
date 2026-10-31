// The wheel review page's panels (PO, WD-22): the thesis as fixed before the first run (Spec ›
// Thesis, WD-21) and each claim's verdict from the results (WD-29); the benchmark table (WD-03);
// the fill model with the mid-vs-print evidence for every option sold and the friction runs
// (WD-31); and the rules, rendered from the config the wheel ran with. Every number is read from
// the results as the page renders.
import { useCallback, useMemo, type ReactNode } from "react";

import { wheelRulePath } from "../../app/pages";
import { KeyValue, RuleLink } from "../../components/cells";
import { Chart } from "../../components/charts/Chart";
import { scatterOption } from "../../components/charts/scatter";
import { DataTable, type TableColumn, type TableDetail } from "../../components/DataTable";
import { Details, Empty, Note } from "../../components/Note";
import { money, moneySigned } from "../../format/money";
import { count, orDash, pct, ratio } from "../../format/number";
import type { Palette } from "../../theme/echarts";
import type {
  RuleTextOut,
  ThesisVerdict,
  WheelFillGroup,
  WheelResult,
} from "../../types/generated/wheel_result";
import { fillPairs } from "../methodology/figures";
import { FitTable, PAIR_COLUMNS, scatterCaption } from "../methodology/sections";

// ---- the thesis -----------------------------------------------------------------------------

/** Each claim as the thesis names it (Spec › Thesis), how its two numbers read, and what its
 * benchmark is when it isn't another strategy's number. */
const CLAIMS: Readonly<Record<number, { name: string; show: (v: number) => string;
                                        bar?: string }>> = {
  1: { name: "It makes money", show: moneySigned, bar: "break-even" },
  2: { name: "It improves Sharpe on the baseline PMCC", show: ratio },
  3: { name: "It beats the S&P 500", show: pct },
};

function claimName(claim: number): string {
  return CLAIMS[claim]?.name ?? `Claim ${String(claim)}`;
}

function claimValue(claim: number, value: number | null): string {
  return orDash(value, CLAIMS[claim]?.show ?? ratio);
}

/** The benchmark's number; making money's is labelled break-even (PO, WD-22). */
function benchmarkValue(claim: number, value: number | null): string {
  const bar = CLAIMS[claim]?.bar;
  const shown = claimValue(claim, value);
  return bar && value !== null ? `${shown} (${bar})` : shown;
}

/** `Met`, or `Not met` in the flag colour. */
function Verdict({ met }: { met: boolean }) {
  return met ? <>Met</> : <span className="pm-flag">Not met</span>;
}

/** The thesis, word for word as the PO fixed it on 2026-10-26, before the first run (WD-21), then
 * how it fared. */
export function Thesis({ run }: { run: WheelResult }) {
  const verdicts = run.summary.thesis;
  const met = verdicts.filter((v) => v.met).length;
  return (
    <Note>
      <p>
        <b>The thesis.</b> Weekly NVDA options are, on average, priced at an implied volatility
        above the volatility NVDA then realizes: the volatility risk premium. A seller of fully
        secured, 0.30-delta weekly options collects that premium every week. Being cash-secured
        and short a single option at a time, the wheel holds at most 100 shares&apos; worth of
        exposure, never levered. The thesis is that:
      </p>
      <ol className="pm-steps">
        <li><b>It makes money:</b> the premiums collected exceed the losses taken when puts are
          assigned below the market and shares are called away below where the stock went.</li>
        <li><b>It improves Sharpe on the baseline PMCC:</b> the wheel carries less delta per
          dollar of capital (about 30 shares&apos; worth while a put is open, about 70 while
          shares are held under a call, on $25,000), so its NAV should swing less. Less exposure
          alone leaves Sharpe unchanged; the claim is that the premium earned is large relative
          to that smaller swing, so its return per unit of volatility is higher than the
          PMCC&apos;s.</li>
        <li><b>It beats the S&amp;P 500</b> over the same period on return.</li>
      </ol>
      <p>
        The thesis was fixed on 2026-10-26, before the first run, and is not edited after it.
        Each claim is met when the wheel&apos;s number is higher than its benchmark&apos;s. Over
        this window, <b>{count(met)} of {count(verdicts.length)} claims are met</b>:{" "}
        {verdicts.map((v, i) => (
          <span key={v.claim}>
            {i > 0 && (i === verdicts.length - 1 ? " and " : ", ")}
            {claimName(v.claim).replace(/^It /, "it ")} {v.met ? "(met)" : "(not met)"}
          </span>
        ))}.
      </p>
    </Note>
  );
}

const VERDICT_COLUMNS: readonly TableColumn<ThesisVerdict>[] = [
  { id: "claim", header: "Claim", num: true, sort: (v) => v.claim, cell: (v) => v.claim },
  { id: "name", header: "The thesis", sort: (v) => claimName(v.claim),
    cell: (v) => claimName(v.claim) },
  { id: "test", header: "Test", sort: (v) => v.test, cell: (v) => v.test },
  { id: "wheel", header: "Wheel", num: true, sort: (v) => v.wheel ?? undefined,
    cell: (v) => claimValue(v.claim, v.wheel) },
  { id: "benchmark", header: "Benchmark", num: true, sort: (v) => v.benchmark ?? undefined,
    cell: (v) => benchmarkValue(v.claim, v.benchmark) },
  { id: "verdict", header: "Verdict", sort: (v) => (v.met ? 0 : 1),
    cell: (v) => <Verdict met={v.met} /> },
];

export function Verdicts({ run }: { run: WheelResult }) {
  return <DataTable label="Verdicts" rows={run.summary.thesis} columns={VERDICT_COLUMNS}
                    rowId={(v) => String(v.claim)} />;
}

// ---- the benchmarks -------------------------------------------------------------------------

interface BenchmarkRow {
  name: string;
  capital: number | null;
  ret: number;
  sharpe: number | null;
  drawdown: number | null;
}

export function benchmarkRows(run: WheelResult): BenchmarkRow[] {
  const { metrics: m, benchmarks: b } = run.summary;
  return [
    { name: run.config.wheel.name, capital: run.starting_cash, ret: m.return_on_starting_cash,
      sharpe: m.sharpe_annualized, drawdown: m.max_drawdown_pct },
    { name: "Baseline PMCC", capital: b.baseline_pmcc.starting_cash,
      ret: b.baseline_pmcc.return_on_starting_cash, sharpe: b.baseline_pmcc.sharpe_annualized,
      drawdown: b.baseline_pmcc.max_drawdown_pct },
    { name: "S&P 500 (price)", capital: null, ret: b.sp500.price_return, sharpe: null,
      drawdown: null },
  ];
}

const BENCHMARK_COLUMNS: readonly TableColumn<BenchmarkRow>[] = [
  { id: "name", header: "Run", sort: (r) => r.name, cell: (r) => r.name },
  { id: "capital", header: "Starting cash", num: true, sort: (r) => r.capital ?? undefined,
    cell: (r) => orDash(r.capital, money) },
  { id: "return", header: "Return", num: true, sort: (r) => r.ret, cell: (r) => pct(r.ret) },
  { id: "sharpe", header: "Sharpe (annualized)", num: true, sort: (r) => r.sharpe ?? undefined,
    cell: (r) => orDash(r.sharpe, ratio) },
  { id: "drawdown", header: "Max drawdown", num: true, sort: (r) => r.drawdown ?? undefined,
    cell: (r) => orDash(r.drawdown, pct) },
];

export function Benchmarks({ run }: { run: WheelResult }) {
  const rows = useMemo(() => benchmarkRows(run), [run]);
  return <DataTable label="Benchmarks" rows={rows} columns={BENCHMARK_COLUMNS}
                    rowId={(r) => r.name} />;
}

export function benchmarkCaption(run: WheelResult): ReactNode {
  const { baseline_pmcc: pmcc, sp500 } = run.summary.benchmarks;
  return (
    <>
      Returns are over the window, not annualized, each on its own starting cash. The baseline
      PMCC is its committed run on {run.manifest.symbol} over the same window at the same r
      ({pmcc.run_id}, config {pmcc.config_hash.slice(0, 8)}). The S&amp;P 500 is its price
      return from the {sp500.start} close ({sp500.start_close.toLocaleString("en-US")}) to the{" "}
      {sp500.end} close ({sp500.end_close.toLocaleString("en-US")}); {sp500.source}. An index has
      no Sharpe or drawdown here: only its return is compared.
    </>
  );
}

// ---- the fill model -------------------------------------------------------------------------

export function FillModel({ run }: { run: WheelResult }) {
  const { fill_model: f } = run.config.wheel;
  const r = run.config.risk_free_rate;
  const e = run.fill_evidence;
  return (
    <div className="pm-stack">
      <Note>
        <p>
          Every option the wheel sells fills at the decision bar&apos;s mid, (bid + ask) ÷ 2; a
          bar without both a bid and an ask fills nothing, and a print is never invented. Held to
          expiry, an option leaves the book by expiring at $0 or by assignment at its strike,
          which is contractual, not a modelling choice. Every decision uses only data up to its
          bar&apos;s end. The scatters below set each print of the options sold against the
          bar&apos;s mid, and the friction runs show how much of the result survives paying part
          of the spread.
        </p>
      </Note>
      <KeyValue
        label="Fill model"
        rows={[
          ["Option fills", "at the mid"],
          ["Spread capture, this run", ratio(f.spread_capture)],
          ["Fee per contract", money(Number(f.fee_per_contract))],
          ["Assignment and call-away", "at the strike"],
          ["Risk-free rate, r", `${pct(r.value, 2)} (${r.series}, as of ${r.as_of})`],
          ["Options sold, whose prints these are", count(e.contracts)],
          ["Prints at or inside the quote, all options", orDash(e.within_spread, pct)],
          ["R² of print on mid, all options", orDash(e.fit?.r2, (v) => v.toFixed(4))],
        ]}
      />
    </div>
  );
}

/** One right's prints against its mids: the scatter, its fit with the share inside the quote,
 * and every pair in a disclosure. */
export function WheelMidVsPrint({ run, group, label }: {
  run: WheelResult;
  group: WheelFillGroup | undefined;
  label: string;
}) {
  const points = group?.points;
  const fit = group?.fit ?? null;
  const build = useCallback(
    (p: Palette) => scatterOption(p, points ?? { mid: [], trade: [], spread: [] }, fit),
    [points, fit],
  );
  const rows = useMemo(() => (points ? fillPairs(points) : []), [points]);
  if (!group || rows.length === 0) return <Empty>No bar had both a print and a valid quote.</Empty>;
  return (
    <>
      <Chart build={build} label={`${label}: print against mid, ${count(rows.length)} pairs`} />
      <FitTable label={`${label} fit`} fits={[[run.manifest.symbol, fit]]}
                extra={[["Prints at or inside the quote", [orDash(group.within_spread, pct)]]]} />
      <Details summary="Values for every pair" table lazy>
        <DataTable label={`${label} pairs`} rows={rows} columns={PAIR_COLUMNS}
                   rowId={(r) => String(r.i)} virtual />
      </Details>
    </>
  );
}

export function wheelScatterCaption(what: string): ReactNode {
  return <>{scatterCaption(what)} Every bar from the sale to the expiry close is counted.</>;
}

// ---- the friction runs ----------------------------------------------------------------------

interface FrictionRow {
  runId: string;
  capture: number;
  pnl: number;
  delta: number;
  ret: number;
  sharpe: number | null;
  drawdown: number;
  verdicts: readonly ThesisVerdict[];
}

/** Each wheel run by its spread capture, at mid first, with its P&L against the run at mid. */
export function frictionRows(runs: readonly WheelResult[], reference: WheelResult): FrictionRow[] {
  const atMid = reference.summary.metrics.pnl;
  return [...runs]
    .sort((a, b) => a.config.wheel.fill_model.spread_capture
      - b.config.wheel.fill_model.spread_capture)
    .map((r) => {
      const m = r.summary.metrics;
      return { runId: r.manifest.run_id, capture: r.config.wheel.fill_model.spread_capture,
               pnl: m.pnl, delta: m.pnl - atMid, ret: m.return_on_starting_cash,
               sharpe: m.sharpe_annualized, drawdown: m.max_drawdown_pct,
               verdicts: r.summary.thesis };
    });
}

/** `1, 2 met · 3 not met`. */
export function verdictText(verdicts: readonly ThesisVerdict[]): string {
  const of = (met: boolean) => verdicts.filter((v) => v.met === met).map((v) => v.claim).join(", ");
  return [of(true) && `${of(true)} met`, of(false) && `${of(false)} not met`]
    .filter(Boolean).join(" · ");
}

function frictionColumns(reference: string): TableColumn<FrictionRow>[] {
  return [
    { id: "capture", header: "Spread capture", num: true, sort: (r) => r.capture,
      cell: (r) => (r.runId === reference ? `${ratio(r.capture)} (at mid, reported)`
        : ratio(r.capture)) },
    { id: "pnl", header: "P&L", num: true, sort: (r) => r.pnl, cell: (r) => moneySigned(r.pnl) },
    { id: "delta", header: "Δ vs at mid", num: true, sort: (r) => r.delta,
      cell: (r) => (r.runId === reference ? "reference" : moneySigned(r.delta)) },
    { id: "return", header: "Return", num: true, sort: (r) => r.ret, cell: (r) => pct(r.ret) },
    { id: "sharpe", header: "Sharpe (annualized)", num: true, sort: (r) => r.sharpe ?? undefined,
      cell: (r) => orDash(r.sharpe, (v) => v.toFixed(3)) },
    { id: "drawdown", header: "Max drawdown", num: true, sort: (r) => r.drawdown,
      cell: (r) => pct(r.drawdown, 2) },
    { id: "claims", header: "Claims", sort: (r) => verdictText(r.verdicts),
      cell: (r) => verdictText(r.verdicts) },
  ];
}

export function Friction({ runs, reference }: {
  runs: readonly WheelResult[];
  reference: WheelResult;
}) {
  const rows = useMemo(() => frictionRows(runs, reference), [runs, reference]);
  const columns = useMemo(() => frictionColumns(reference.manifest.run_id), [reference]);
  return <DataTable label="Friction runs" rows={rows} columns={columns} rowId={(r) => r.runId} />;
}

// ---- the rules ------------------------------------------------------------------------------

interface RuleRow {
  id: string;
  text: RuleTextOut | undefined;
}

function hint(text: RuleTextOut | undefined): string | undefined {
  return text ? `${text.condition} → ${text.action}` : undefined;
}

function paragraphs(text: string): ReactNode {
  return text.split("\n").map((p, i) => <p key={i}>{p}</p>);
}

const WHY: TableDetail<RuleRow> = {
  header: "Why",
  label: (row) => `Rationale for ${row.id}`,
  render: (row) => (row.text ? paragraphs(row.text.rationale) : undefined),
};

function ruleColumns(symbol: string): TableColumn<RuleRow>[] {
  return [
    { id: "id", header: "ID", sort: (r) => r.id,
      cell: (r) => <RuleLink id={r.id} to={wheelRulePath(symbol, r.id)} title={hint(r.text)} /> },
    { id: "rule", header: "Rule", sort: (r) => r.text?.title ?? r.id,
      cell: (r) => <div className="pm-prose">{r.text?.title ?? r.id}</div> },
    { id: "happens", header: "What happens", sort: (r) => r.text?.summary,
      cell: (r) => <div className="pm-prose" title={hint(r.text)}>{r.text?.summary}</div> },
  ];
}

/** The wheel's rules in the config's order, each in plain words with its reasoning under a
 * toggle; `#/wheel-review/:symbol/<ID>` outlines and scrolls to that rule. */
export function WheelRules({ run, target }: { run: WheelResult; target: string | undefined }) {
  const rows = useMemo(() => run.config.wheel.rules.map((r) => ({ id: r.id, text: run.rule_text[r.id] })),
                       [run]);
  const columns = useMemo(() => ruleColumns(run.manifest.symbol), [run]);
  const known = target === undefined || rows.some((r) => r.id === target);
  return (
    <>
      {!known && <Empty>The rule this link names isn&apos;t in these results.</Empty>}
      <DataTable label="Wheel rules" rows={rows} columns={columns} rowId={(r) => r.id}
                 detail={WHY} target={target} wrap grow />
    </>
  );
}

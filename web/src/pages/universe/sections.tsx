// The universe page's tables (UI-SPEC §6.5): the suitability screen, each measure over the weeks
// it could be read, with its caption naming the quant rules it reads (DEC-66, DEC-113); and the
// headline by symbol, the comparison page's headline columns after the symbol, which links to
// that symbol's comparison page (DEC-111).
import { useMemo } from "react";
import { Link } from "react-router-dom";

import { RuleLink, Stacked } from "../../components/cells";
import { DataTable, type TableColumn } from "../../components/DataTable";
import { orDash, pct, ratio, spreadPct } from "../../format/number";
import type { Headline } from "../../types/generated/headline";
import type { RuleOut } from "../../types/generated/rules";
import type { Suitability as SuitabilityFile, SuitabilityRow } from "../../types/generated/suitability";
import { HEADLINE_COLUMNS } from "../compare/sections";
import type { HeadlineRow } from "../compare/figures";

// ---- symbol suitability -----------------------------------------------------------------------

function weeks(n: number): string {
  return `${n} ${n === 1 ? "week" : "weeks"}`;
}

/** A measure over the weeks it was read: its value, the count under it. */
function measure(value: number | null, format: (v: number) => string, over: number) {
  return <Stacked top={orDash(value, format)} sub={weeks(over)} />;
}

/** A rule as a hover shows it: `condition → action`; empty when the rules aren't loaded. */
function hint(rules: readonly RuleOut[], id: string): string {
  const rule = rules.find((r) => r.id === id);
  return rule ? `${rule.condition} → ${rule.action}` : "";
}

function suitabilityColumns(rules: readonly RuleOut[]): TableColumn<SuitabilityRow>[] {
  return [
    { id: "symbol", header: "Symbol", sort: (r) => r.symbol,
      cell: (r) => <span className="pm-label">{r.symbol}</span> },
    { id: "extrinsic", header: "Long extrinsic per delta (% of spot)", num: true,
      sort: (r) => r.long_extrinsic_per_delta_pct_spot ?? undefined,
      cell: (r) => measure(r.long_extrinsic_per_delta_pct_spot, pct, r.long_weeks) },
    { id: "spread", header: "Median spread (long / short)", num: true,
      sort: (r) => r.median_spread_long_pct ?? undefined,
      cell: (r) => (
        <Stacked top={`${orDash(r.median_spread_long_pct, spreadPct)} / ${
                       orDash(r.median_spread_short_pct, spreadPct)}`}
                 sub={`${r.long_weeks} / ${weeks(r.short_weeks)}`} />) },
    { id: "credit", header: "Weekly credit after half-spread (% of long cost)", num: true,
      sort: (r) => r.weekly_credit_after_half_spread_pct_long_cost ?? undefined,
      cell: (r) => measure(r.weekly_credit_after_half_spread_pct_long_cost, pct, r.short_weeks) },
    { id: "vrp", header: "IV ÷ RV20", num: true, sort: (r) => r.iv_over_rv20 ?? undefined,
      cell: (r) => measure(r.iv_over_rv20, ratio, r.iv_rv20_weeks) },
    { id: "event", header: "Event week fires", num: true,
      sort: (r) => (r.g3_weeks > 0 ? r.g3_fires / r.g3_weeks : undefined),
      cell: (r) => (
        <Stacked top={<RuleLink id="G-3" title={hint(rules, "G-3")}>
                        {r.g3_fires} of {weeks(r.g3_weeks)}
                      </RuleLink>}
                 sub={`ratio above ${ratio(r.g3_max_ratio)}`} />) },
  ];
}

export function Suitability({ suitability, rules }: {
  suitability: SuitabilityFile;
  /** Quant's rules, for the event-week gate's hover. */
  rules: readonly RuleOut[];
}) {
  const columns = useMemo(() => suitabilityColumns(rules), [rules]);
  return <DataTable label="Symbol suitability" rows={suitability.rows} columns={columns}
                    rowId={(r) => r.symbol} />;
}

function Named({ rules, id }: { rules: readonly RuleOut[]; id: string }) {
  const name = rules.find((r) => r.id === id)?.name ?? "rule";
  return <RuleLink id={id} title={hint(rules, id)} prose>{name.toLowerCase()}</RuleLink>;
}

/** How the screen is read (DEC-66), each quant rule it reads named and linked (DEC-113). */
export function SuitabilityCaption({ rules }: { rules: readonly RuleOut[] }) {
  return (
    <>
      Read once a week, at the first bar of each week-open session, from what quant would pick
      there, whether or not it traded that week: the long by its{" "}
      <Named rules={rules} id="E-L3" /> rule (the least extrinsic value per delta) and the short
      by its <Named rules={rules} id="E-S3" /> rule (at or beyond the week&apos;s expected move).
      Each measure is over the weeks it could be read, counted under it. The credit is the
      short&apos;s bid ÷ the long&apos;s mid; IV ÷ RV20 is the front week&apos;s ATM IV over its
      20-day realized volatility, as the <Named rules={rules} id="G-4" /> gate reads it; the event
      week count is the weeks the <Named rules={rules} id="G-3" /> gate fired at quant&apos;s
      threshold, of the weeks it could be checked.
    </>
  );
}

// ---- headline by symbol -----------------------------------------------------------------------

type SymbolRow = HeadlineRow & { symbol: string };

const BY_SYMBOL_COLUMNS: readonly TableColumn<SymbolRow>[] = [
  { id: "symbol", header: "Symbol", sort: (r) => r.symbol,
    cell: (r) => <Link to={`/compare/${r.symbol}`}>{r.symbol}</Link> },
  ...(HEADLINE_COLUMNS as readonly TableColumn<SymbolRow>[]),
];

/** The file's rows as the headline shows them: each symbol in the file's order, quant first. */
export function symbolRows(headline: Headline, name: (strategyId: string) => string,
                           quantId: string): SymbolRow[] {
  const order = [...new Set(headline.rows.map((r) => r.symbol))];
  const rank = (r: Headline["rows"][number]) =>
    order.indexOf(r.symbol) * 2 + Number(r.strategy_id !== quantId);
  return [...headline.rows].sort((a, b) => rank(a) - rank(b)).map((r) => ({
    id: `${r.symbol}/${r.strategy_id}`,
    symbol: r.symbol,
    name: name(r.strategy_id),
    pnl: r.pnl,
    returnOnNav: r.return_on_starting_nav,
    maxDrawdown: r.max_drawdown,
    maxDrawdownPct: null,
    sharpe: r.sharpe_annualized,
    payoff: r.payoff_ratio,
    weekly: r.weekly_return,
  }));
}

export function HeadlineBySymbol({ headline, name, quantId }: {
  headline: Headline;
  /** A strategy's name, from its ID. */
  name: (strategyId: string) => string;
  /** The strategy listed first within each symbol. */
  quantId: string;
}) {
  const rows = useMemo(() => symbolRows(headline, name, quantId), [headline, name, quantId]);
  return <DataTable label="Headline by symbol" rows={rows} columns={BY_SYMBOL_COLUMNS}
                    rowId={(r) => r.id} />;
}

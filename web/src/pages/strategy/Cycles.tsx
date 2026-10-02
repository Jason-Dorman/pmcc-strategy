// Strategy [3], cycle statistics (UI-SPEC §6.2; DEC-62): one cycle is one week. Weeks traded and
// skipped, the skips by reason, win rate, average win and loss, payoff, premium captured, the
// weekly credit against the long's cost, and the exit mix. Skips and exits read in plain words,
// each linked to its rule (PO, DEC-107).
import { Fragment } from "react";

import { KeyValue, RuleLink } from "../../components/cells";
import { Empty } from "../../components/Note";
import { money } from "../../format/money";
import { orDash, pct, ratio } from "../../format/number";
import { ruleHint, ruleLabel } from "../../format/rule";
import type { RunResult } from "../../types/generated/run_result";

/** Rules with their counts, each in plain words and linked to its rule:
 * `Structure fails 5 · Low vol premium 11` (PO, DEC-107). */
export function RuleCounts({ counts, run }: {
  counts: Record<string, number> | null;
  run: RunResult;
}) {
  const entries = Object.entries(counts ?? {});
  if (entries.length === 0) return <>none</>;
  return (
    <>
      {entries.map(([id, n], i) => (
        <Fragment key={id}>
          {i > 0 && " · "}
          <RuleLink id={id} title={ruleHint(id, run.rule_text) || undefined}>
            {ruleLabel(id, run.config.strategy.rules)}
          </RuleLink> {n}
        </Fragment>
      ))}
    </>
  );
}

export function Cycles({ run }: { run: RunResult }) {
  const { cycle_stats: c, skips_by_rule: skips, exit_mix: exits } = run.summary;
  if (!c) return <Empty>This run&apos;s summary has no cycle statistics.</Empty>;
  const held = `over ${c.weeks_long_held} weeks a long was held`;
  return (
    <KeyValue
      label="Cycle statistics"
      rows={[
        ["Weeks traded / skipped", `${c.weeks_traded} / ${c.weeks_skipped}, of ${c.weeks}`],
        ["Skips, by reason", <RuleCounts key="skips" counts={skips} run={run} />],
        [`Win rate, ${held}`, orDash(c.win_rate, pct)],
        ["Average win / loss",
         `${orDash(c.average_win, money)} / ${orDash(c.average_loss, money)}`],
        ["Payoff (average win ÷ |average loss|)", orDash(c.payoff_ratio, ratio)],
        ["Premium captured (Σ(credit − buyback) ÷ Σ credit)",
         orDash(c.premium_captured_pct, pct)],
        ["Weekly credit, % of the long's cost", orDash(c.credit_pct_of_long_cost, pct)],
        ["Exit mix", <RuleCounts key="exits" counts={exits} run={run} />],
      ]}
    />
  );
}

// Wheel [3], cycle statistics (Spec › Metrics; PO, WD-20, WD-29): the weeks sold and skipped (the
// skips by reason, in plain words and linked), how each put and call ended, the complete cycles
// and whether one is open at the end, the premium, and the share of bars in each state.
import { KeyValue } from "../../components/cells";
import { money } from "../../format/money";
import { count, pct } from "../../format/number";
import { stateLabel } from "../../format/wheel";
import type { WheelResult } from "../../types/generated/wheel_result";
import { weeksSkipped } from "./figures";
import { WheelRuleCounts } from "./rule";

const STATES = ["put", "shares", "call", "cash"] as const;

export function Cycles({ run }: { run: WheelResult }) {
  const c = run.summary.cycle_stats;
  const open = c.open_at_end ? ", one more open at the end" : "";
  return (
    <KeyValue
      label="Cycle statistics"
      rows={[
        ["Weeks sold / skipped", `${count(c.weeks_sold)} / ${count(weeksSkipped(run))}, of ${
          count(c.weeks)}`],
        ["Skips, by reason", <WheelRuleCounts key="skips" counts={c.weeks_skipped} run={run} />],
        ["Puts sold", `${count(c.puts_sold)}: ${count(c.puts_expired)} expired, ${
          count(c.puts_assigned)} assigned`],
        ["Calls sold", `${count(c.calls_sold)}: ${count(c.calls_expired)} expired, ${
          count(c.calls_called_away)} called away`],
        ["Complete cycles (assigned, then called away)", `${count(c.complete_cycles)}${open}`],
        ["Premium collected, net of fees", money(c.premium)],
        ...STATES.map((s): readonly [string, string] => [
          `Bars in ${stateLabel(s).toLowerCase()}`, pct(c.time_in_state[s] ?? 0),
        ]),
      ]}
    />
  );
}

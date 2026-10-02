// Strategy [2], Reg T (UI-SPEC §6.2): the account at the last bar, its lowest available funds and
// when, and how many bars breached. A breach means the position couldn't have been held in a real
// Reg T account, and the panel says so in a warning.
import { KeyValue } from "../../components/cells";
import { Empty } from "../../components/Note";
import { WarningBanner } from "../../components/WarningBanner";
import { money } from "../../format/money";
import { count } from "../../format/number";
import { timeET } from "../../format/time";
import type { RunResult } from "../../types/generated/run_result";
import { breaches, minFunds } from "./figures";

export function RegT({ run }: { run: RunResult }) {
  const ledger = run.ledger ?? [];
  const last = ledger.at(-1);
  const low = minFunds(ledger);
  if (!last || !low) return <Empty>This run&apos;s file has no ledger.</Empty>;
  const breached = breaches(run);
  return (
    <>
      {breached > 0 && (
        <WarningBanner>
          Available funds were below zero on {count(breached)} bars: this position couldn&apos;t
          have been held in a real Reg T account.
        </WarningBanner>
      )}
      <KeyValue
        label="Reg T"
        rows={[
          ["Starting cash", money(run.starting_cash)],
          ["NAV, at the end", money(last.nav)],
          ["Initial margin (IM), at the end", money(last.im)],
          ["Maintenance margin (MM), at the end", money(last.mm)],
          ["Available funds, at the end", money(last.available_funds)],
          ["Excess equity, at the end", money(last.excess_equity)],
          ["Min available funds", `${money(low.available_funds)}, ${timeET(low.time)}`],
          ["Bars with available funds below zero", count(breached)],
        ]}
      />
    </>
  );
}

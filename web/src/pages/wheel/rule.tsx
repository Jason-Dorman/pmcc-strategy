// A wheel rule wherever the wheel's pages name one (WD-22): what it did in plain words, its
// condition → action on hover, linked to its row on the wheel review page. The PMCC PO's copy
// rules, kept for the wheel (PO, WD-22): never the ID outside an ID column.
import { Fragment, type ReactNode } from "react";

import { wheelRulePath } from "../../app/pages";
import { RuleLink } from "../../components/cells";
import { ruleHint, ruleLabel } from "../../format/rule";
import type { WheelResult } from "../../types/generated/wheel_result";

export function WheelRule({ id, run, children }: {
  id: string;
  run: WheelResult;
  children?: ReactNode;
}) {
  return (
    <RuleLink id={id} to={wheelRulePath(run.manifest.symbol, id)}
              title={ruleHint(id, run.rule_text) || undefined}>
      {children ?? ruleLabel(id, run.config.wheel.rules)}
    </RuleLink>
  );
}

/** Rules with their counts, each in plain words and linked: `Cash short 2 · No liquid bar 1`. */
export function WheelRuleCounts({ counts, run }: {
  counts: Record<string, number>;
  run: WheelResult;
}) {
  const entries = Object.entries(counts);
  if (entries.length === 0) return <>none</>;
  return (
    <>
      {entries.map(([id, n], i) => (
        <Fragment key={id}>
          {i > 0 && " · "}
          <WheelRule id={id} run={run} /> {n}
        </Fragment>
      ))}
    </>
  );
}

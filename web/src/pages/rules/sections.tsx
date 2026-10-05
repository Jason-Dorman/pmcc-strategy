// The Trade rules page's panels (UI-SPEC §6.3), all from rules.json (DEC-52): how rules work, the
// entry, gate and exit tables, each row a rule's title and summary in plain words with its live
// values and its reasoning under a toggle (PO, DEC-114), the ablations and the sensitivity runs.
// Each rule's row is `#/rules/<ID>`'s target.
import { Fragment, type ReactNode } from "react";

import { RuleLink } from "../../components/cells";
import { DataTable, type TableColumn, type TableDetail } from "../../components/DataTable";
import { Note } from "../../components/Note";
import { money } from "../../format/money";
import type { RuleOut, Rules } from "../../types/generated/rules";
import {
  changed,
  CHECK_NAMES,
  differences,
  fillChanges,
  paramChanges,
  paramWords,
  ruleRows,
  sameRule,
  versions,
  variantRows,
  type Changed,
  type Pair,
  type RuleRow,
  type Section,
  type VariantRow,
} from "./model";

function hint(rule: RuleOut | undefined): string | undefined {
  return rule ? `${rule.condition} → ${rule.action}` : undefined;
}

/** A rule's ID, linked to its own row (a link a reader can copy). */
function Id({ row }: { row: RuleRow }) {
  return <RuleLink id={row.id} title={hint(row.quant ?? row.baseline)} />;
}

/** A rule by its name, linked to its row: the page's copy never names a rule by its ID (PO,
 * DEC-113). */
function Named({ id, rule }: { id: string; rule: RuleOut | undefined }) {
  return <RuleLink id={id} title={hint(rule)} prose>{rule?.name ?? id}</RuleLink>;
}

/** Rules by name, each linked, listed as a sentence lists them: `A, B and C`. */
function Names({ pair, ids }: { pair: Pair; ids: readonly string[] }) {
  const rows = ruleRows(pair);
  return (
    <>
      {ids.map((id, i) => {
        const row = rows.find((r) => r.id === id);
        return (
          <Fragment key={id}>
            {i > 0 && (i === ids.length - 1 ? " and " : ", ")}
            <Named id={id} rule={row?.quant ?? row?.baseline} />
          </Fragment>
        );
      })}
    </>
  );
}

// ---- how rules work ---------------------------------------------------------------------------

const COUNTS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"];

/** How the strategies differ, in words (PO, DEC-114), where the rules bear it out: they share every
 * rule but entry rules both run differently and gates only quant runs. Otherwise each rule that
 * differs is named. */
function Differ({ pair }: { pair: Pair }) {
  const d = differences(pair);
  const [quant, baseline] = [pair.quant.name, pair.baseline.name];
  if (d.other.length === 0 && d.baselineGates.length === 0) {
    const filters = COUNTS[d.quantGates.length] ?? String(d.quantGates.length);
    return (
      <p>
        <b>{baseline} and {quant} manage positions the same way.</b> They differ only in how they
        choose the long and short calls
        {d.quantGates.length > 0 && <>, plus {filters} extra filters used by {quant}</>}. That
        means any performance difference comes from contract selection and trade filtering, not
        different exit rules.
      </p>
    );
  }
  const names = (ids: readonly string[]) => <Names pair={pair} ids={ids} />;
  const clauses: ReactNode[] = [];
  if (d.selection.length > 0) clauses.push(<Fragment key="s">their {names(d.selection)} rules</Fragment>);
  if (d.quantGates.length > 0) {
    clauses.push(<Fragment key="q">the {names(d.quantGates)} gates, which only{" "}
      {quant} runs</Fragment>);
  }
  if (d.baselineGates.length > 0) {
    clauses.push(<Fragment key="b">the {names(d.baselineGates)} gates, which only{" "}
      {baseline} runs</Fragment>);
  }
  if (d.other.length > 0) clauses.push(<Fragment key="o">their {names(d.other)} rules</Fragment>);
  return (
    <p>
      <b>{baseline} and {quant} differ in</b>{" "}
      {clauses.map((c, i) => (
        <Fragment key={i}>{i > 0 && (i === clauses.length - 1 ? ", and in " : ", in ")}{c}</Fragment>
      ))}.
    </p>
  );
}

export function HowRulesWork({ pair, ruleId }: { pair: Pair; ruleId: string | undefined }) {
  const known = ruleRows(pair).some((r) => r.id === ruleId);
  return (
    <Note>
      {ruleId !== undefined && !known && (
        <p><b>The rule this link names isn&apos;t in these results.</b></p>
      )}
      <p>Every decision is made at the end of an hourly bar, in the same order each session:</p>
      <ol className="pm-steps">
        <li>Check whether the long call needs to be exited or replaced.</li>
        <li>Check whether the short call needs to be closed.</li>
        <li>On the first trading day of the week, sell a new short call if no skip-week gate
          blocks the trade.</li>
      </ol>
      <p>
        If more than one gate could apply, we stop at the first one and log exactly what triggered
        it.
      </p>
      <Differ pair={pair} />
      <p>
        Every blotter row and gate-log entry links here to the rule behind it, and the ID column
        gives each rule&apos;s reference in the results. Each row reads with the values the runs
        used, from the configs they ran with; ▸ opens the reasoning.
      </p>
    </Note>
  );
}

// ---- the rule tables --------------------------------------------------------------------------

/** A rule's row in plain words (PO, DEC-114); the rule stated exactly on hover. */
function Summary({ rule }: { rule: RuleOut }) {
  return <div className="pm-prose" title={hint(rule)}>{rule.summary}</div>;
}

function NotRun() {
  return <span className="pm-label">not run</span>;
}

/** A rule's summary both strategies share, or each strategy's, labelled. */
function Summaries({ row, pair }: { row: RuleRow; pair: Pair }) {
  const { baseline, quant } = row;
  if (!baseline || !quant || sameRule(baseline, quant)) {
    const one = quant ?? baseline;
    return one ? <Summary rule={one} /> : null;
  }
  return (
    <>
      <div className="pm-prose" title={hint(baseline)}>
        <span className="pm-label">{pair.baseline.name}:</span> {baseline.summary}
      </div>
      <div className="pm-prose" title={hint(quant)}>
        <span className="pm-label">{pair.quant.name}:</span> {quant.summary}
      </div>
    </>
  );
}

function paragraphs(text: string): ReactNode {
  return text.split("\n").map((p, i) => <p key={i}>{p}</p>);
}

/** The reasoning under a rule's row: one both strategies share, or each one's. */
function rationale(pair: Pair): TableDetail<RuleRow> {
  return {
    header: "Why",
    label: (row) => `Rationale for ${row.id}`,
    render: (row) => {
      const v = versions(row, (r) => r.rationale);
      if (v.kind === "shared") return paragraphs(v.text);
      return (
        <>
          {v.baseline !== undefined && <><p className="pm-label">{pair.baseline.name}</p>
            {paragraphs(v.baseline)}</>}
          {v.quant !== undefined && <><p className="pm-label">{pair.quant.name}</p>
            {paragraphs(v.quant)}</>}
        </>
      );
    },
  };
}

const idColumn: TableColumn<RuleRow> = {
  id: "id", header: "ID", sort: (r) => r.id, cell: (r) => <Id row={r} />,
};

const titleOf = (r: RuleRow) => (r.quant ?? r.baseline)?.title ?? r.id;
const summaryOf = (r: RuleRow) => (r.quant ?? r.baseline)?.summary;

const titleColumn = (header: string): TableColumn<RuleRow> => ({
  id: "rule", header, sort: titleOf, cell: (r) => <div className="pm-prose">{titleOf(r)}</div>,
});

function entryColumns(): TableColumn<RuleRow>[] {
  const same = (r: RuleRow) =>
    r.baseline !== undefined && r.quant !== undefined && sameRule(r.baseline, r.quant);
  return [
    idColumn,
    titleColumn("Rule"),
    { id: "baseline", header: "Baseline", sort: (r) => r.baseline?.summary,
      cell: (r) => (r.baseline ? <Summary rule={r.baseline} /> : <NotRun />) },
    { id: "quant", header: "Quant", sort: (r) => (same(r) ? "Same" : r.quant?.summary),
      cell: (r) => {
        if (same(r)) return <span className="pm-label">Same</span>;
        return r.quant ? <Summary rule={r.quant} /> : <NotRun />;
      } },
  ];
}

/** A gate on or off for a strategy, with the threshold it runs at: `On · 1.20`. */
function OnOff({ rule }: { rule: RuleOut | undefined }) {
  if (!rule) return <span className="pm-label">Off</span>;
  const shown = Object.entries(rule.shown);
  const title = shown.map(([name, value]) => `${paramWords(name)} ${value}`).join(" · ");
  return <span title={title || undefined}>{["On", ...shown.map(([, v]) => v)].join(" · ")}</span>;
}

const onOffText = (rule: RuleOut | undefined) =>
  rule ? `On ${Object.values(rule.shown).join(" ")}` : "Off";

function gateColumns(pair: Pair): TableColumn<RuleRow>[] {
  return [
    idColumn,
    titleColumn("Gate"),
    { id: "condition", header: "Condition", sort: summaryOf,
      cell: (r) => <Summaries row={r} pair={pair} /> },
    { id: "baseline", header: "Baseline", sort: (r) => onOffText(r.baseline),
      cell: (r) => <OnOff rule={r.baseline} /> },
    { id: "quant", header: "Quant", sort: (r) => onOffText(r.quant),
      cell: (r) => <OnOff rule={r.quant} /> },
  ];
}

function exitColumns(pair: Pair): TableColumn<RuleRow>[] {
  return [
    idColumn,
    titleColumn("Rule"),
    { id: "happens", header: "What happens", sort: summaryOf,
      cell: (r) => <Summaries row={r} pair={pair} /> },
  ];
}

const TABLES: Readonly<Record<Section, { label: string; columns: (pair: Pair) => TableColumn<RuleRow>[] }>> = {
  entry: { label: "Entry rules", columns: entryColumns },
  gate: { label: "Skip-week gates", columns: gateColumns },
  exit: { label: "Exit rules", columns: exitColumns },
};

/** One section's rules, both strategies side by side, the target row outlined. */
export function RuleTable({ pair, section, target }: {
  pair: Pair;
  section: Section;
  target: string | undefined;
}) {
  const { label, columns } = TABLES[section];
  return (
    <DataTable label={label} rows={ruleRows(pair, section)} columns={columns(pair)}
               rowId={(r) => r.id} detail={rationale(pair)} target={target} wrap grow />
  );
}

// ---- the ablations ----------------------------------------------------------------------------

interface AblationRow extends Changed {
  row: VariantRow;
}

/** What took a removed layer's place: the variant's rule, its new values, or nothing. */
function ReplacedBy({ c }: { c: Changed }) {
  if (c.change.change === "removed" || !c.after) return <span className="pm-label">nothing</span>;
  if (c.change.change === "params") {
    return <div className="pm-prose">{paramChanges(c.before, c.after).join(" · ")}</div>;
  }
  return <div className="pm-prose" title={hint(c.after)}>{c.after.summary}</div>;
}

const ablationColumns: TableColumn<AblationRow>[] = [
  { id: "ablation", header: "Ablation", sort: (r) => r.row.variant.name,
    cell: (r) => <div className="pm-prose">{r.row.variant.name}</div> },
  { id: "removed", header: "Layer removed", sort: (r) => r.before?.name,
    cell: (r) => (
      <div className="pm-prose">
        {r.before ? <Named id={r.change.rule_id} rule={r.before} /> : "—"}
      </div>
    ) },
  { id: "replaced", header: "Replaced by", sort: (r) => r.after?.summary ?? "",
    cell: (r) => <ReplacedBy c={r} /> },
];

export function Ablations({ rules }: { rules: Rules }) {
  const rows = variantRows(rules, ["ablation"])
    .flatMap((row) => changed(row).map((c) => ({ ...c, row })));
  return (
    <DataTable label="Ablations" rows={rows} columns={ablationColumns} wrap
               rowId={(r) => `${r.row.variant.id}:${r.change.rule_id}`} />
  );
}

// ---- the sensitivity runs ---------------------------------------------------------------------

/** One rule a variant changed, by the rule's name: `Short leg strike: k 1.0 → 0.75`, `Entry
 * trigger: replaced by Entry trigger, fixed bar · bar 1`, `Event week: removed`. */
function RuleChangeText({ c }: { c: Changed }) {
  const values = paramChanges(c.before, c.after);
  const words: Record<string, string[]> = {
    params: values,
    replaced: [`replaced by ${c.after?.name ?? ""}`, ...values],
    removed: ["removed"],
    added: ["added", ...values],
    text: ["reworded"],
  };
  return (
    <>
      <Named id={c.change.rule_id} rule={c.before ?? c.after} />:{" "}
      {(words[c.change.change] ?? [c.change.change]).join(" · ")}
    </>
  );
}

function Change({ row }: { row: VariantRow }) {
  const fill = fillChanges(row, money);
  const rules = changed(row);
  return (
    <div className="pm-prose">
      {fill.join(" · ")}
      {rules.map((c, i) => (
        <Fragment key={c.change.rule_id}>
          {(fill.length > 0 || i > 0) && "; "}
          <RuleChangeText c={c} />
        </Fragment>
      ))}
    </div>
  );
}

const changeText = (row: VariantRow) =>
  [...fillChanges(row, money), ...changed(row).map((c) => (c.before ?? c.after)?.name)].join(" ");

const sensitivityColumns: TableColumn<VariantRow>[] = [
  { id: "check", header: "Check", sort: (r) => CHECK_NAMES[r.family],
    cell: (r) => CHECK_NAMES[r.family] },
  { id: "run", header: "Run", sort: (r) => r.variant.name,
    cell: (r) => <div className="pm-prose">{r.variant.name}</div> },
  { id: "change", header: "Change", sort: changeText, cell: (r) => <Change row={r} /> },
];

export function Sensitivity({ rules }: { rules: Rules }) {
  const rows = variantRows(rules, ["friction", "timing", "grid"]);
  return (
    <DataTable label="Sensitivity" rows={rows} columns={sensitivityColumns} wrap
               rowId={(r) => r.variant.id}
               filters={[{ id: "check", name: "Check", offer: (r) => [CHECK_NAMES[r.family]] }]} />
  );
}

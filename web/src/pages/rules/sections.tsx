// The Trade rules page's panels (UI-SPEC §6.3), all from rules.json (DEC-52): how rules work, the
// entry, gate and exit tables with each rule's live values and its rationale under a toggle, the
// ablations and the sensitivity runs. Each rule's row is `#/rules/<ID>`'s target.
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
  type Versions,
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

function Differ({ pair }: { pair: Pair }) {
  const d = differences(pair);
  const [quant, baseline] = [pair.quant.name, pair.baseline.name];
  const names = (ids: readonly string[]) => <Names pair={pair} ids={ids} />;
  const clauses: ReactNode[] = [];
  if (d.selection.length > 0) {
    clauses.push(<Fragment key="s">their {names(d.selection)} rules, which select the
      contracts</Fragment>);
  }
  if (d.quantGates.length > 0) {
    clauses.push(<Fragment key="q">the {names(d.quantGates)} gates, which only{" "}
      {quant} runs</Fragment>);
  }
  if (d.baselineGates.length > 0) {
    clauses.push(<Fragment key="b">the {names(d.baselineGates)} gates, which only{" "}
      {baseline} runs</Fragment>);
  }
  if (d.other.length > 0) clauses.push(<Fragment key="o">their {names(d.other)} rules</Fragment>);
  if (clauses.length === 0) return <p>{baseline} and {quant} run the same rules.</p>;
  return (
    <p>
      <b>{baseline} and {quant} differ only in</b>{" "}
      {clauses.map((c, i) => (
        <Fragment key={i}>{i > 0 && (i === clauses.length - 1 ? ", and in " : ", in ")}{c}</Fragment>
      ))}.
      {d.other.length === 0 && (
        <> Every other rule, every exit included, is the same in both, so a difference in their
          results comes from selection and gates, not from how the positions are managed.</>
      )}
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
      <p>
        Every decision is made at the end of an hourly bar, in the same order each session: first
        the long leg&apos;s exits and resets, then the short&apos;s exits, then, in the week-open
        session only, the week&apos;s new short, sold only if no skip-week gate fires. The gates
        are checked in order, and the first to fire is logged with the values that fired it.
      </p>
      <Differ pair={pair} />
      <p>
        Every blotter row and gate-log entry links here to the rule behind it, and the ID column
        gives each rule&apos;s reference in the results. Each rule reads with the values the runs
        used, from the configs they ran with; ▸ opens its rationale.
      </p>
    </Note>
  );
}

// ---- the rule tables --------------------------------------------------------------------------

/** A rule's condition, then its action. */
function Said({ rule }: { rule: RuleOut }) {
  return (
    <>
      <div className="pm-prose">{rule.condition}</div>
      <div className="pm-prose pm-then">→ {rule.action}</div>
    </>
  );
}

function NotRun() {
  return <span className="pm-label">not run</span>;
}

/** Text both strategies share, or each strategy's, labelled. */
function Texts({ v, pair }: { v: Versions; pair: Pair }) {
  if (v.kind === "shared") return <div className="pm-prose">{v.text}</div>;
  return (
    <>
      <div className="pm-prose"><span className="pm-label">{pair.baseline.name}:</span>{" "}
        {v.baseline ?? <NotRun />}</div>
      <div className="pm-prose"><span className="pm-label">{pair.quant.name}:</span>{" "}
        {v.quant ?? <NotRun />}</div>
    </>
  );
}

function paragraphs(text: string): ReactNode {
  return text.split("\n").map((p, i) => <p key={i}>{p}</p>);
}

/** The rationale under a rule's row: one both strategies share, or each one's. */
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

const nameOf = (r: RuleRow) => (r.quant ?? r.baseline)?.name ?? r.id;

function entryColumns(): TableColumn<RuleRow>[] {
  const same = (r: RuleRow) =>
    r.baseline !== undefined && r.quant !== undefined && sameRule(r.baseline, r.quant);
  return [
    idColumn,
    { id: "rule", header: "Rule", sort: nameOf, cell: nameOf },
    { id: "baseline", header: "Baseline", sort: (r) => r.baseline?.condition,
      cell: (r) => (r.baseline ? <Said rule={r.baseline} /> : <NotRun />) },
    { id: "quant", header: "Quant", sort: (r) => (same(r) ? "Same" : r.quant?.condition),
      cell: (r) => {
        if (same(r)) return <span className="pm-label">Same</span>;
        return r.quant ? <Said rule={r.quant} /> : <NotRun />;
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
    { id: "gate", header: "Gate", sort: nameOf, cell: nameOf },
    { id: "condition", header: "Condition", sort: (r) => (r.quant ?? r.baseline)?.condition,
      cell: (r) => {
        const differ = r.baseline && r.quant && !sameRule(r.baseline, r.quant);
        const one = differ ? undefined : (r.quant ?? r.baseline);
        if (one) return <Said rule={one} />;
        return <Texts v={versions(r, (rule) => `${rule.condition} → ${rule.action}`)} pair={pair} />;
      } },
    { id: "baseline", header: "Baseline", sort: (r) => onOffText(r.baseline),
      cell: (r) => <OnOff rule={r.baseline} /> },
    { id: "quant", header: "Quant", sort: (r) => onOffText(r.quant),
      cell: (r) => <OnOff rule={r.quant} /> },
  ];
}

function exitColumns(pair: Pair): TableColumn<RuleRow>[] {
  const trigger = (rule: RuleOut) => `${rule.name}: ${rule.condition}`;
  return [
    idColumn,
    { id: "trigger", header: "Trigger", sort: (r) => (r.quant ?? r.baseline)?.name,
      cell: (r) => <Texts v={versions(r, trigger)} pair={pair} /> },
    { id: "action", header: "Action", sort: (r) => (r.quant ?? r.baseline)?.action,
      cell: (r) => <Texts v={versions(r, (rule) => rule.action)} pair={pair} /> },
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
  return <div className="pm-prose" title={c.after.condition}>{c.after.action}</div>;
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
  { id: "replaced", header: "Replaced by", sort: (r) => r.after?.action ?? "",
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

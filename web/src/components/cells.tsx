// Table cells shared by the pages (UI-SPEC §5): a rule ID linked to its rule, a value over a
// muted line (a RIC over its OCC symbol, spaces kept), and the key/value table.
import type { ReactNode } from "react";
import { Link } from "react-router-dom";

import type { InstrumentOut } from "../types/generated/run_result";

/** A rule, linked to `#/rules/<ID>` (UI-SPEC §7): its ID in mono, or what the caller shows. A
 * rule named in prose takes the prose's type (`prose`). */
export function RuleLink({ id, title, children, prose = false }: {
  id: string;
  title?: string | undefined;
  children?: ReactNode;
  prose?: boolean;
}) {
  return (
    <Link className={prose ? "pm-rule pm-rule-prose" : "pm-rule"} to={`/rules/${id}`}
          title={title}>
      {children ?? id}
    </Link>
  );
}

/** A value with a muted second line under it. */
export function Stacked({ top, sub, title }: { top: ReactNode; sub: ReactNode; title?: string }) {
  return (
    <div title={title}>
      <div>{top}</div>
      <div className="pm-subcell">{sub}</div>
    </div>
  );
}

/** An instrument: its RIC, and the OCC symbol under it (the stock has none). */
export function Instrument({ instrument }: { instrument: InstrumentOut }) {
  return <Stacked top={instrument.ric} sub={instrument.occ ?? "stock"} />;
}

export type KeyValueRow = readonly [label: ReactNode, value: ReactNode];

/** A key/value table: labels muted on the left, values mono on the right. */
export function KeyValue({ label, rows }: { label: string; rows: readonly KeyValueRow[] }) {
  return (
    <table className="pm-table pm-table-kv" aria-label={label}>
      <tbody>
        {rows.map(([key, value], i) => (
          <tr key={i}>
            <td>{key}</td>
            <td className="pm-num">{value}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

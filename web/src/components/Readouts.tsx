// The KPI strip under the command bar (UI-SPEC §2): a muted label, an amber mono value, and a
// one-line hint defining the number.
export interface Readout {
  label: string;
  value: string;
  hint: string;
}

export function Readouts({ items }: { items: readonly Readout[] }) {
  return (
    <div className="pm-readouts">
      {items.map((item) => (
        <div className="pm-readout" key={item.label}>
          <div className="pm-readout-label">{item.label}</div>
          <div className="pm-readout-value">{item.value}</div>
          <div className="pm-readout-hint">{item.hint}</div>
        </div>
      ))}
    </div>
  );
}

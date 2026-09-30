// Comparison, the landing page (UI-SPEC §6.1). The panels are built at P7-02.
import { useParams } from "react-router-dom";

import { pending, PageFrame } from "../components/PageFrame";
import { useRun } from "../data/useRun";
import { W_FULL, W_HALF } from "../theme/tokens";
import { panel, toCome, whenLoaded } from "./placeholder";

export function Comparison() {
  const { symbol = "" } = useParams();
  const baseline = useRun(symbol, "baseline_pmcc");
  const quant = useRun(symbol, "quant_pmcc");
  const manifests = [baseline, quant].flatMap((r) => (r.kind === "ready" ? [r.value.manifest] : []));
  const bars = (r: typeof quant) =>
    whenLoaded(r, (run) => toCome("P7-02", `${run.manifest.run_id}: ${run.ledger?.length ?? 0} bars`));
  return (
    <PageFrame
      readouts={pending([
        ["Quant P&L", "Ending NAV − starting cash"],
        ["Baseline P&L", "Ending NAV − starting cash"],
        ["Quant − Baseline", "The quant layer's P&L over the baseline"],
        ["Quant return on capital", "P&L ÷ peak long-leg cost"],
        ["Quant weekly-return 95% CI", "Bootstrap, 10,000 resamples"],
        ["Weeks traded (Q / B)", "Weeks a short was sold"],
      ])}
      panels={[
        panel("purpose", "Purpose", W_FULL, toCome("P7-02"), false),
        panel("nav", "NAV — baseline vs quant", W_FULL, <>{bars(baseline)}{bars(quant)}</>),
        panel("headline", "Headline", W_HALF, toCome("P7-02")),
        panel("pooled", "Pooled universe", W_HALF, toCome("P7-02")),
        panel("ablations", "Ablations", W_FULL, toCome("P7-02")),
      ]}
      manifests={manifests}
    />
  );
}

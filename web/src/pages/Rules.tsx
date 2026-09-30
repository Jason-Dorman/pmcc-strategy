// Trade rules (UI-SPEC §6.3), rendered from rules.json at P7-03. `#/rules/X-S3` will scroll to
// and outline that rule.
import { useParams } from "react-router-dom";

import { PageFrame } from "../components/PageFrame";
import { W_FULL, W_HALF } from "../theme/tokens";
import { panel, toCome } from "./placeholder";

export function Rules() {
  const { ruleId } = useParams();
  const detail = ruleId ? `rule ${ruleId}` : undefined;
  return (
    <PageFrame
      panels={[
        panel("how", "How rules work", W_FULL, toCome("P7-03", detail), false),
        panel("entry", "Entry rules", W_FULL, toCome("P7-03")),
        panel("gates", "Skip-week gates", W_FULL, toCome("P7-03")),
        panel("exits", "Exit rules", W_FULL, toCome("P7-03")),
        panel("ablations", "Ablations", W_HALF, toCome("P7-03")),
        panel("sensitivity", "Sensitivity", W_HALF, toCome("P7-03")),
      ]}
    />
  );
}

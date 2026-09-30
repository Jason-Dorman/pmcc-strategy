// Universe (UI-SPEC §6.5), built at P7-05.
import { PageFrame } from "../components/PageFrame";
import { W_FULL } from "../theme/tokens";
import { panel, toCome } from "./placeholder";

export function Universe() {
  const later = toCome("P7-05");
  return (
    <PageFrame
      panels={[
        panel("suitability", "Symbol suitability", W_FULL, later),
        panel("headline", "Headline by symbol", W_FULL, later),
        panel("pooled", "Pooled universe", W_FULL, later),
      ]}
    />
  );
}

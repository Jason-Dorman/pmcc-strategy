// Methodology (UI-SPEC §6.4), built at P7-04.
import { PageFrame } from "../components/PageFrame";
import { W_FULL, W_HALF } from "../theme/tokens";
import { panel, toCome } from "./placeholder";

export function Methodology() {
  const later = toCome("P7-04");
  return (
    <PageFrame
      panels={[
        panel("ric", "Data and RIC scheme", W_HALF, later, false),
        panel("coverage", "Data coverage", W_HALF, later),
        panel("timing", "Bar timing and look-ahead guard", W_FULL, later, false),
        panel("fills", "Fill model", W_FULL, later, false),
        panel("shorts", "Mid vs print — weekly shorts", W_HALF, later),
        panel("longs", "Mid vs print — long-dated longs", W_HALF, later),
        panel("regt", "Reg T treatment", W_FULL, later, false),
        panel("friction", "Friction", W_HALF, later),
        panel("entry", "Entry timing", W_HALF, later),
        panel("grid", "Parameter grid", W_FULL, later),
        panel("assumptions", "Stated assumptions", W_FULL, later),
      ]}
    />
  );
}

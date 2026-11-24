// The volatility thesis's page (T4-01; UI-SPEC §6 › Thesis; PO, TD-10, TD-28): the assignment's
// items in their order, over `thesis.json` as the nightly run last left it. A file whose next
// night is overdue is marked stale, whatever it says of itself (THESIS-SPEC §9).
import type { ReactNode } from "react";

import { longDate } from "../components/charts/axis";
import { pending, PageFrame } from "../components/PageFrame";
import type { Readout } from "../components/Readouts";
import { WarningBanner } from "../components/WarningBanner";
import { useThesis } from "../data/useRun";
import { orDash } from "../format/number";
import { bps, creditLabel, evidenceLabel, isStale, level, signalDetail, signalLabel, thesisLabel,
         volPts } from "../format/thesis";
import { timeET } from "../format/time";
import { W_FULL, W_HERO, W_SIDECAR } from "../theme/tokens";
import type { Thesis as ThesisFile } from "../types/generated/thesis";
import { panel, whenLoaded } from "./placeholder";
import { AlphaCost, Conditions, HistoricalEvidence } from "./thesis/evidence";
import { Horizons, Macro, Methodology, TheThesis } from "./thesis/prose";
import { CreditSpread, TodaysState, Tracker } from "./thesis/tracker";

const READOUT_HINTS = [
  ["Thesis status", "Two of the three wrong-if conditions need a backtest"],
  ["Evidence", "Too few matured episodes to classify"],
  ["Today's signal", ""],
  ["Data through", "The last session in the tracker"],
  ["VIX minus forecast", "VIX less the 30-day volatility forecast, in volatility points"],
  ["Credit", "The high-yield spread as known at the decision"],
] as const;

const PENDING = pending(READOUT_HINTS.map(([l, h]) => [l, h]));

function statusHint(t: ThesisFile): string {
  return t.thesis_status === "PAUSED" ? "The first wrong-if condition is triggered"
    : READOUT_HINTS[0][1];
}

function readouts(t: ThesisFile): Readout[] {
  const c = t.current;
  const shown: readonly (readonly [string, string])[] = [
    [thesisLabel(t.thesis_status), statusHint(t)],
    [evidenceLabel(t.evidence_status), READOUT_HINTS[1][1]],
    [signalLabel(t.signal.status), signalDetail(t.signal)],
    [orDash(t.data_through, longDate), `Updated ${timeET(t.generated_at)}`],
    [orDash(c?.forecast_gap_vol, volPts),
     c === null ? READOUT_HINTS[4][1] : `VIX ${orDash(c.vix, level)} less the 30-day forecast`],
    [c === null ? "—" : creditLabel(c.credit_status),
     c === null ? READOUT_HINTS[5][1] : `${orDash(c.credit_bps, bps)} as known at the decision`],
  ];
  return READOUT_HINTS.map(([label], i) => {
    const [value, hint] = shown[i] ?? ["—", ""];
    return { label, value, hint };
  });
}

function StaleBanner({ thesis }: { thesis: ThesisFile }) {
  if (!isStale(thesis)) return null;
  return (
    <WarningBanner>
      Stale: the tracker&apos;s last successful update was {timeET(thesis.generated_at)}, with data
      through {orDash(thesis.data_through, longDate)}. A later nightly run is overdue or failed.
    </WarningBanner>
  );
}

export function Thesis() {
  const state = useThesis();
  const body = (render: (t: ThesisFile) => ReactNode) => whenLoaded(state, render);
  return (
    <>
      {state.kind === "ready" && <StaleBanner thesis={state.value} />}
      <PageFrame
        readouts={state.kind === "ready" ? readouts(state.value) : PENDING}
        panels={[
          panel("thesis", "The thesis", W_FULL, <TheThesis />, false),
          panel("horizons", "Time horizons", W_FULL, <Horizons />, false),
          { ...panel("tracker", "Daily tracker", W_FULL, body((t) => <Tracker thesis={t} />)),
            note: "updated after each session by the nightly run" },
          { ...panel("credit", "Credit spread", W_HERO, body((t) => <CreditSpread thesis={t} />)),
            note: "ICE BofA US High Yield OAS, via FRED" },
          { ...panel("state", "Today's state", W_SIDECAR, body((t) => <TodaysState thesis={t} />),
                     false),
            note: "measured, at the last session's close" },
          { ...panel("conditions", "Wrong-if conditions", W_FULL,
                     body((t) => <Conditions thesis={t} />)),
            note: "what would prove the thesis wrong",
            caption: <>The first is a current rolling assessment, recomputed each night. Persistent
              failure tracking and the controls for resuming after a failure are not implemented in
              this milestone. Too small a sample is shown as insufficient data, never as a
              pass.</> },
          { ...panel("evidence", "Preliminary historical evidence", W_HERO,
                     body((t) => <HistoricalEvidence thesis={t} />)),
            note: "matured 30-day outcomes only" },
          { ...panel("cost", "Alpha and cost", W_SIDECAR, body((t) => <AlphaCost thesis={t} />),
                     false),
            note: "gross economic premium, not tradable alpha" },
          panel("macro", "Macro environment", W_FULL, body((t) => <Macro thesis={t} />), false),
          panel("methodology", "Methodology and sources", W_FULL,
                body((t) => <Methodology thesis={t} />), false),
        ]}
      />
    </>
  );
}

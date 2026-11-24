// The volatility thesis's page (T4-02; UI-SPEC §6 › Thesis; PO, TD-30): a reading sequence, from the
// idea to the methodology, over `thesis.json` as the nightly run last left it. Its look is its own
// (theme/thesis.css), not the terminal's. The idea and the macro paragraph need no data, so they
// show whatever the file's state.
import { WarningBanner } from "../components/WarningBanner";
import { Empty, Loading } from "../components/Note";
import type { Loaded } from "../data/state";
import { useThesis } from "../data/useRun";
import type { Thesis as ThesisFile } from "../types/generated/thesis";
import { Cost } from "./thesis/cost";
import { Evidence } from "./thesis/evidence";
import { Idea, Macro } from "./thesis/idea";
import { Invalidate } from "./thesis/invalidate";
import { Assessment } from "./thesis/latest";
import { Methodology } from "./thesis/methodology";
import { Contents } from "./thesis/parts";
import { Tracker } from "./thesis/tracker";

function NoFile({ state }: { state: Exclude<Loaded<ThesisFile>, { kind: "ready" }> }) {
  if (state.kind === "loading") return <Loading />;
  if (state.kind === "mismatch") return <WarningBanner>{state.message}</WarningBanner>;
  return (
    <Empty>
      {state.kind === "missing" ? "The tracker has not published a file yet." : state.message}
    </Empty>
  );
}

export function Thesis() {
  const state = useThesis();
  const thesis = state.kind === "ready" ? state.value : null;
  return (
    <main className="th">
      <Idea />
      <Contents />
      {state.kind !== "ready" && <NoFile state={state} />}
      {thesis && (
        <>
          <Assessment thesis={thesis} />
          <Tracker thesis={thesis} />
          <Evidence thesis={thesis} />
          <Invalidate thesis={thesis} />
          <Cost thesis={thesis} />
        </>
      )}
      <Macro />
      {thesis && <Methodology thesis={thesis} />}
    </main>
  );
}

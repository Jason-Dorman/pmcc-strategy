// The route table (UI-SPEC §7, DEC-73). App wraps it in a HashRouter; tests in a MemoryRouter.
import { Navigate, Route, Routes } from "react-router-dom";

import { Empty, Loading } from "../components/Note";
import { useIndex } from "../data/IndexContext";
import { Comparison } from "../pages/Comparison";
import { Data } from "../pages/Data";
import { Methodology } from "../pages/Methodology";
import { Rules } from "../pages/Rules";
import { Strategy } from "../pages/Strategy";
import { Universe } from "../pages/Universe";
import { AppShell } from "./AppShell";

/** `#/` opens the comparison page of the index's first symbol. */
function Home() {
  const index = useIndex();
  if (index.kind === "loading") return <Loading />;
  const first = index.kind === "ready" ? index.value.symbols[0]?.symbol : undefined;
  return first ? <Navigate to={`/compare/${first}`} replace /> : <Empty>No results yet.</Empty>;
}

export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Home />} />
        <Route path="compare/:symbol" element={<Comparison />} />
        <Route path="baseline/:symbol" element={<Strategy page="baseline" />} />
        <Route path="quant/:symbol" element={<Strategy page="quant" />} />
        <Route path="rules/:ruleId?" element={<Rules />} />
        <Route path="methodology/:symbol?" element={<Methodology />} />
        <Route path="universe" element={<Universe />} />
        <Route path="data/:symbol?" element={<Data />} />
        <Route path="*" element={<Empty>No such page.</Empty>} />
      </Route>
    </Routes>
  );
}

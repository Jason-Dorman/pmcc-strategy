// The route table (UI-SPEC §7, DEC-73). App wraps it in a HashRouter; tests in a MemoryRouter.
import { Route, Routes } from "react-router-dom";

import { Empty } from "../components/Note";
import { Comparison } from "../pages/Comparison";
import { Data } from "../pages/Data";
import { Home } from "../pages/Home";
import { Live } from "../pages/Live";
import { Methodology } from "../pages/Methodology";
import { Rules } from "../pages/Rules";
import { Strategy } from "../pages/Strategy";
import { Universe } from "../pages/Universe";
import { Wheel } from "../pages/Wheel";
import { WheelReview } from "../pages/WheelReview";
import { AppShell } from "./AppShell";

// `#/` is the home page: the site's strategies, each linked to its pages (PO, LD-36).
export function AppRoutes() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<Home />} />
        <Route path="compare/:symbol" element={<Comparison />} />
        <Route path="baseline/:symbol" element={<Strategy page="baseline" />} />
        <Route path="quant/:symbol" element={<Strategy page="quant" />} />
        <Route path="wheel/:symbol" element={<Wheel />} />
        <Route path="wheel-review/:symbol/:ruleId?" element={<WheelReview />} />
        <Route path="live/:symbol" element={<Live />} />
        <Route path="rules/:ruleId?" element={<Rules />} />
        <Route path="methodology/:symbol?" element={<Methodology />} />
        <Route path="universe" element={<Universe />} />
        <Route path="data/:symbol?" element={<Data />} />
        <Route path="*" element={<Empty>No such page.</Empty>} />
      </Route>
    </Routes>
  );
}

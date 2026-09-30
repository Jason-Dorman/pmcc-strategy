// The app (ARCHITECTURE §13): HashRouter, since GitHub Pages has no SPA fallback, so a deep link
// such as #/quant/NVDA survives a refresh (DEC-73); the index loads once, at startup.
import { HashRouter } from "react-router-dom";

import { IndexProvider } from "../data/IndexContext";
import { AppRoutes } from "./routes";

export function App() {
  return (
    <HashRouter>
      <IndexProvider>
        <AppRoutes />
      </IndexProvider>
    </HashRouter>
  );
}

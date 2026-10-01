// The smoke test (P4-08, INV-15): every route for one symbol, on the built site served as Pages
// serves it (`vite preview` over web/dist), in Chromium. Build first: `just e2e` exports the
// results and builds the site before it runs.
import { defineConfig, devices } from "@playwright/test";

const PORT = 4174;
export const BASE_URL = `http://127.0.0.1:${PORT}/`;

export default defineConfig({
  testDir: "e2e",
  outputDir: "test-results/playwright",
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: BASE_URL, ...devices["Desktop Chrome"] },
  webServer: {
    command: `npx vite preview --host 127.0.0.1 --port ${PORT} --strictPort`,
    url: BASE_URL,
    reuseExistingServer: false,
  },
});

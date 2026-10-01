// The smoke test (P4-08, INV-15): every route loads for one symbol, as built, with no console
// error, no request to any origin but the site's own, the manifest footer present, and no page
// wider than the screen. Each route is screenshotted at the four widths UI-SPEC §10 reviews; CI
// uploads them (test-results/screenshots).
import { expect, test, type Page } from "@playwright/test";

const SYMBOL = "NVDA";
const ROUTES = [
  "",
  `compare/${SYMBOL}`,
  `baseline/${SYMBOL}`,
  `quant/${SYMBOL}`,
  "rules",
  "rules/X-S3",
  `methodology/${SYMBOL}`,
  "universe",
  `data/${SYMBOL}`,
];
const WIDTHS = [390, 1100, 1366, 1600];
const HEIGHT = 1000;

interface Watched {
  errors: string[];
  foreign: string[];
}

/** Console errors, uncaught exceptions and requests to another origin, from here on. */
function watch(page: Page, origin: string): Watched {
  const watched: Watched = { errors: [], foreign: [] };
  page.on("console", (message) => {
    if (message.type() === "error") watched.errors.push(message.text());
  });
  page.on("pageerror", (error) => watched.errors.push(error.message));
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.protocol !== "data:" && url.origin !== origin) watched.foreign.push(request.url());
  });
  return watched;
}

/** The page has loaded its data: the footer is up and no panel is still loading. */
async function settled(page: Page): Promise<void> {
  await expect(page.getByRole("contentinfo", { name: "Run manifest" })).toBeVisible();
  await expect(page.getByRole("status", { name: "Loading" })).toHaveCount(0);
  await expect(page.getByText("PMCC Backtest", { exact: true })).toBeVisible();
}

for (const route of ROUTES) {
  test(`#/${route} loads cleanly at every width`, async ({ page, baseURL }) => {
    const origin = new URL(baseURL ?? "").origin;
    const watched = watch(page, origin);

    await page.goto(`./#/${route}`);
    await settled(page);

    for (const width of WIDTHS) {
      await page.setViewportSize({ width, height: HEIGHT });
      await settled(page);
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth,
      );
      expect(overflow, `#/${route} scrolls sideways at ${width} px`).toBeLessThanOrEqual(0);
      const name = route === "" ? "home" : route.replaceAll("/", "_");
      await page.screenshot({ path: `test-results/screenshots/${name}-${width}.png`, fullPage: true });
    }

    expect(watched.errors, "console errors").toEqual([]);
    expect(watched.foreign, "cross-origin requests").toEqual([]);
  });
}

test("a deep link survives a reload", async ({ page }) => {
  await page.goto(`./#/quant/${SYMBOL}`);
  await settled(page);
  await page.reload();
  await settled(page);
  await expect(page.getByRole("region", { name: "Gate log" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Quant" })).toHaveAttribute("aria-current", "page");
});

test("real results show no synthetic banner", async ({ page }) => {
  await page.goto(`./#/compare/${SYMBOL}`);
  await settled(page);
  await expect(page.getByText("Synthetic data — not market results.")).toHaveCount(0);
});

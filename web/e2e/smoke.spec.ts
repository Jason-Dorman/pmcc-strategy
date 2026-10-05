// The smoke test (P4-08, INV-15): every route loads for one symbol, as built, with no console
// error, no request to any origin but the site's own, the manifest footer present, and no page
// wider than the screen. Each route is screenshotted at the four widths UI-SPEC §10 reviews; CI
// uploads them (test-results/screenshots).
import { expect, test, type Page } from "@playwright/test";

import { TABLE_ROW_HEIGHT } from "../src/theme/tokens";

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

test("the strategy pages show the run's numbers, charts and tables", async ({ page }) => {
  for (const strategy of ["baseline", "quant"]) {
    await page.goto(`./#/${strategy}/${SYMBOL}`);
    await settled(page);
    const label = page.locator(".pm-readout-label", { hasText: /^Ending NAV$/ });
    const nav = page.locator(".pm-readout", { has: label }).locator(".pm-readout-value");
    await expect(nav).toHaveText(/^\$\d{1,3}(,\d{3})*\.\d{2}$/);
    const account = page.getByRole("figure", { name: /available funds/ });
    await expect(account.locator("svg path").first()).toBeAttached();
    const blotter = page.getByRole("table", { name: "Blotter" });
    await expect(blotter.locator("tbody tr:not(.pm-spacer)").first()).toBeVisible();
    // The ledger is virtualized: some of its hourly bars render, never all of them.
    const ledger = page.getByRole("table", { name: "Ledger" }).locator("tbody tr:not(.pm-spacer)");
    await expect(ledger.first()).toBeVisible();
    expect(await ledger.count()).toBeLessThan(200);
  }
  await page.getByRole("table", { name: "Blotter" }).getByRole("link").first().click();
  await expect(page).toHaveURL(/#\/rules\/[A-Z]-[A-Z0-9]+$/);
});

test("the comparison page shows both runs, the pooled universe and the ablations", async ({ page }) => {
  await page.goto(`./#/compare/${SYMBOL}`);
  await settled(page);
  const label = page.locator(".pm-readout-label", { hasText: /^Quant − Baseline$/ });
  const gap = page.locator(".pm-readout", { has: label }).locator(".pm-readout-value");
  await expect(gap).toHaveText(/^[+−]?\$\d{1,3}(,\d{3})*\.\d{2}$/);
  const nav = page.getByRole("figure", { name: /NAV on every bar/ });
  await expect(nav.locator("svg path").first()).toBeAttached();
  const rows = (name: string) =>
    page.getByRole("table", { name, exact: true }).locator("tbody tr:not(.pm-spacer)");
  await expect(rows("Headline")).toHaveCount(2);
  await expect(rows("Pooled universe").first()).toBeVisible();
  expect(await rows("Ablations").count()).toBeGreaterThan(1);
  // The purpose's sentence on the result's main limit reads both runs' legs (DEC-109).
  await expect(page.getByRole("region", { name: "Purpose" })).toContainText("the long leg made");
});

test("the methodology page draws every pair, its tables and the limits", async ({ page }) => {
  await page.goto(`./#/methodology/${SYMBOL}`);
  await settled(page);
  for (const name of ["Mid vs print — weekly shorts", "Mid vs print — long-dated longs"]) {
    const region = page.getByRole("region", { name });
    await expect(region.getByRole("figure").locator("svg path").first()).toBeAttached();
    await expect(region.getByRole("table", { name: `${name} fit` }).locator("tbody tr"))
      .toHaveCount(6);
  }
  // Every pair's table is built only when its disclosure opens, then scrolls virtualized.
  const shorts = page.getByRole("region", { name: "Mid vs print — weekly shorts" });
  await shorts.getByText("Values for every pair").click();
  const pairs = shorts.getByRole("table", { name: "Mid vs print — weekly shorts pairs" });
  await expect(pairs.locator("tbody tr:not(.pm-spacer)").first()).toBeVisible();
  const rows = (name: string) =>
    page.getByRole("table", { name, exact: true }).locator("tbody tr:not(.pm-spacer)");
  for (const name of ["Parameter grid", "Friction", "Entry timing"]) {
    expect(await rows(name).count(), name).toBeGreaterThan(1);
  }
  // Fragility follows DEC-67; the limits' figures are read from the runs (DEC-109).
  await expect(page.getByRole("table", { name: "Timing dispersion" }))
    .toContainText(/(Not fragile|Fragile):/);
  await expect(page.getByRole("region", { name: "Limits of this backtest" }))
    .toContainText("long leg made");
});

test("the universe page shows the screen, the headline by symbol and the pooled universe",
     async ({ page }) => {
  await page.goto("./#/universe");
  await settled(page);
  const rows = (name: string) =>
    page.getByRole("table", { name, exact: true }).locator("tbody tr:not(.pm-spacer)");
  await expect(rows("Symbol suitability").first()).toContainText(SYMBOL);
  await expect(rows("Pooled universe").first()).toBeVisible();
  // Two strategies per symbol, quant first, each row linked to its comparison page (DEC-111).
  const headline = rows("Headline by symbol");
  expect(await headline.count()).toBeGreaterThanOrEqual(2);
  await expect(headline.first()).toContainText("Quant PMCC");
  // The footer traces the figures to the runs they came from.
  await expect(page.getByRole("contentinfo")).toContainText(`${SYMBOL} quant_pmcc`);
  await headline.first().getByRole("link", { name: SYMBOL }).click();
  await expect(page).toHaveURL(new RegExp(`#/compare/${SYMBOL}$`));
});

test("a trade's rule link lands on that rule's row, outlined and in view", async ({ page }) => {
  await page.goto(`./#/quant/${SYMBOL}`);
  await settled(page);
  const link = page.getByRole("table", { name: "Gate log" }).getByRole("link").first();
  await link.click();
  await expect(page).toHaveURL(/#\/rules\/[A-Z]-[A-Z0-9]+$/);
  const id = page.url().split("/").at(-1) ?? "";
  const target = page.locator("tr.pm-target");
  await expect(target).toHaveCount(1);
  await expect(target.getByRole("link", { name: id, exact: true })).toBeVisible();
  await expect(target).toBeInViewport();
});

test("the rules page sets both strategies' rules side by side, from rules.json", async ({ page }) => {
  await page.goto("./#/rules");
  await settled(page);
  const rows = (name: string) =>
    page.getByRole("table", { name, exact: true }).locator("tbody tr:not(.pm-spacer)");
  await expect(rows("Entry rules")).toHaveCount(10);
  await expect(rows("Skip-week gates")).toHaveCount(5);
  await expect(rows("Exit rules")).toHaveCount(8);
  await expect(rows("Ablations").first()).toBeVisible();
  await expect(rows("Sensitivity").first()).toBeVisible();
  const gates = page.getByRole("table", { name: "Skip-week gates" });
  await expect(gates.locator("tr", { hasText: "G-3" })).toContainText("On · 1.20");
  await page.getByRole("button", { name: "Rationale for X-S5" }).click();
  await expect(page.getByText(/never exercised on purpose/)).toBeVisible();
});

// ---- the adversarial review's regressions (P7-01 review, DEC-106) ------------------------------

/** Each chart's week labels (`Mar 30`), left to right, with their horizontal extents. */
async function weekLabels(page: Page) {
  return page.locator('[role="figure"] svg').evaluateAll((svgs) =>
    svgs.map((svg) =>
      [...svg.querySelectorAll("text")]
        .filter((t) => /^[A-Z][a-z]{2} \d{1,2}$/.test(t.textContent ?? ""))
        .map((t) => {
          const box = t.getBoundingClientRect();
          return { text: t.textContent ?? "", left: box.left, right: box.right, top: box.top };
        })
        .sort((a, b) => a.left - b.left)));
}

test("week labels never overlap, and the first week is always labelled", async ({ page }) => {
  await page.goto(`./#/quant/${SYMBOL}`);
  await settled(page);
  const ident = (await page.locator(".pm-ident").textContent()) ?? "";
  const start = /(\d{4})-(\d{2})-(\d{2}) →/.exec(ident);
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const first = start ? `${months[Number(start[2]) - 1]} ${Number(start[3])}` : "";
  for (const width of WIDTHS) {
    await page.setViewportSize({ width, height: HEIGHT });
    await settled(page);
    const charts = await weekLabels(page);
    expect(charts.length, `charts at ${width} px`).toBeGreaterThanOrEqual(3);
    for (const labels of charts) {
      expect(labels[0]?.text, `first label at ${width} px`).toBe(first);
      for (let i = 1; i < labels.length; i++) {
        const [a, b] = [labels[i - 1], labels[i]];
        if (a && b && Math.abs(a.top - b.top) < 1) {
          expect(b.left, `${a.text} | ${b.text} at ${width} px`).toBeGreaterThanOrEqual(a.right);
        }
      }
    }
  }
});

test("the ledger scrolls through every bar, in order, none blank", async ({ page }) => {
  await page.goto(`./#/quant/${SYMBOL}`);
  await settled(page);
  const ledger = page.getByRole("table", { name: "Ledger" });
  await expect(ledger.locator("tbody tr:not(.pm-spacer)").first()).toBeVisible();
  // Every bar's time, as the page shows it, from the run's own file.
  const times = await page.evaluate(async () => {
    const index = await (await fetch("data/index.json")).json();
    const entry = index.symbols[0].runs.find((r: { run_id: string }) => r.run_id === "quant_pmcc");
    const result = await (await fetch(`data/${entry.path}`)).json();
    const et = new Intl.DateTimeFormat("en-CA", {
      timeZone: "America/New_York", year: "numeric", month: "2-digit", day: "2-digit",
      hour: "2-digit", minute: "2-digit", hourCycle: "h23",
    });
    return result.ledger.map((row: { time: string }) => {
      const p = Object.fromEntries(et.formatToParts(new Date(row.time)).map((x) => [x.type, x.value]));
      return `${p.year}-${p.month}-${p.day} ${p.hour}:${p.minute} ET`;
    }) as string[];
  });
  expect(times.length).toBeGreaterThan(100);
  const scroller = ledger.locator("xpath=..");
  for (const target of [0, Math.floor(times.length / 2), times.length - 1]) {
    await scroller.evaluate((el, top) => { el.scrollTop = top; }, target * TABLE_ROW_HEIGHT);
    await page.waitForTimeout(100);
    const shown = await ledger.locator("tbody tr:not(.pm-spacer) td:first-child").allTextContents();
    const at = shown.map((t) => times.indexOf(t));
    expect(at.every((i) => i >= 0), `rows near bar ${target}`).toBe(true);
    expect(at, `rows near bar ${target} are contiguous`).toEqual(
      at.map((_, k) => (at[0] ?? 0) + k));
    expect(at, `the bar at the top of the view, ${target}`).toContain(
      Math.min(target, times.length - 1));
  }
});

test("a sort clicked as soon as the page loads takes effect", async ({ page }) => {
  await page.goto(`./#/quant/${SYMBOL}`);
  const ledger = page.getByRole("table", { name: "Ledger" });
  const nav = ledger.getByRole("columnheader", { name: "NAV" });
  await nav.getByRole("button").click();
  await expect(nav).toHaveAttribute("aria-sort", "ascending");
  const shown = await ledger.locator("tbody tr:not(.pm-spacer) td:nth-child(12)").allTextContents();
  const values = shown.map((t) => Number(t.replace(/[^\d.]/g, "")));
  expect(values.length).toBeGreaterThan(1);
  expect(values, "NAV ascending").toEqual([...values].sort((a, b) => a - b));
});

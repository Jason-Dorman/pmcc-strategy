// Percentages, ratios and Greeks (UI-SPEC §9): percent to 1 dp (a spread under 1% to 2), δ and
// ratios to 2 dp, IV as a percent to 1 dp. Negatives take a true minus sign, as money does.
const MINUS = "−";

function fixed(value: number, digits: number): string {
  const text = Math.abs(value).toFixed(digits);
  return value < 0 && Number(text) !== 0 ? `${MINUS}${text}` : text;
}

/** A fraction as a percent: `0.2202` → `22.0%`. */
export function pct(fraction: number, digits = 1): string {
  return `${fixed(fraction * 100, digits)}%`;
}

/** A bid/ask spread as a percent of mid: 2 dp under 1%, else 1 dp. */
export function spreadPct(fraction: number): string {
  return pct(fraction, Math.abs(fraction) < 0.01 ? 2 : 1);
}

/** A ratio or a delta, to 2 dp. */
export function ratio(value: number): string {
  return fixed(value, 2);
}

/** An implied volatility as a percent, to 1 dp. */
export function iv(value: number): string {
  return pct(value, 1);
}

/** Whole numbers grouped by thousands, a true minus on a negative (short shares). */
export function count(value: number): string {
  const text = Math.abs(value).toLocaleString("en-US");
  return value < 0 ? `${MINUS}${text}` : text;
}

/** `—` for a value the result doesn't have; the formatted value otherwise. */
export function orDash<T>(value: T | null | undefined, format: (v: T) => string): string {
  return value === null || value === undefined ? "—" : format(value);
}

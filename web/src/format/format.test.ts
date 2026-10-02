import { describe, expect, it } from "vitest";

import { short } from "./hash";
import { money, moneySigned, moneyTick, price } from "./money";
import { count, iv, orDash, pct, ratio, spreadPct } from "./number";
import { timeET } from "./time";

describe("money", () => {
  it("groups thousands and shows cents", () => {
    expect(money(12345.67)).toBe("$12,345.67");
  });
  it("uses a true minus sign", () => {
    expect(money(-1234)).toBe("\u2212$1,234.00");
  });
  it("never shows a minus on zero", () => {
    expect(money(-0.001)).toBe("$0.00");
  });
});

describe("price", () => {
  it("shows the four places a price is quantized to", () => {
    expect(price(2.345)).toBe("$2.3450");
  });
});

describe("timeET", () => {
  it("shows a result time in New York time", () => {
    expect(timeET("2026-09-14T10:00:00-04:00")).toBe("2026-09-14 10:00 ET");
  });
  it("converts a UTC time to New York time", () => {
    expect(timeET("2026-12-01T15:00:00Z")).toBe("2026-12-01 10:00 ET");
  });
});

describe("short", () => {
  it("keeps the first eight characters by default", () => {
    expect(short("beb2b55f2f8dc760")).toBe("beb2b55f");
  });
});

describe("moneyTick", () => {
  it("shortens thousands to one place, a k after", () => {
    expect(moneyTick(15200)).toBe("$15.2k");
    expect(moneyTick(-2455)).toBe("\u2212$2.5k");
  });
  it("keeps whole dollars under a thousand", () => {
    expect(moneyTick(-850)).toBe("\u2212$850");
    expect(moneyTick(0)).toBe("$0");
  });
});

describe("moneySigned", () => {
  it("shows a gain's plus and a loss's true minus", () => {
    expect(moneySigned(803.5)).toBe("+$803.50");
    expect(moneySigned(-2455)).toBe("\u2212$2,455.00");
  });
  it("shows no sign on zero, or on what rounds to it", () => {
    expect(moneySigned(0)).toBe("$0.00");
    expect(moneySigned(0.001)).toBe("$0.00");
  });
});

describe("percent and ratios", () => {
  it("shows a fraction as a percent to one place, a true minus on a loss", () => {
    expect(pct(0.220233)).toBe("22.0%");
    expect(pct(-2.055383)).toBe("\u2212205.5%");
    expect(pct(-0.00001)).toBe("0.0%");
  });
  it("shows a spread under 1% to two places", () => {
    expect(spreadPct(0.007547)).toBe("0.75%");
    expect(spreadPct(0.025347)).toBe("2.5%");
  });
  it("shows a ratio or a delta to two places", () => {
    expect(ratio(1.105527)).toBe("1.11");
    expect(ratio(-0.951)).toBe("\u22120.95");
  });
  it("shows an IV as a percent", () => {
    expect(iv(0.558737)).toBe("55.9%");
  });
  it("groups counts and dashes a missing value", () => {
    expect(count(10000)).toBe("10,000");
    expect(count(-100)).toBe("−100"); // short shares take a true minus
    expect(orDash(null, pct)).toBe("—");
    expect(orDash(0.5, pct)).toBe("50.0%");
  });
});

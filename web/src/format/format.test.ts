import { describe, expect, it } from "vitest";

import { short } from "./hash";
import { money, price } from "./money";
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

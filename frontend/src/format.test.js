import { describe, expect, it } from "vitest";
import { formatDate, formatMoney, formatNumber, formatPercent, humanize } from "./format.js";

describe("format helpers", () => {
  it("formats money", () => {
    expect(formatMoney("1234.5")).toBe("$1,234.50");
    expect(formatMoney(2500000, true)).toBe("$2.5M");
    expect(formatMoney(null)).toBe("$0.00");
    expect(formatMoney("abc")).toBe("-");
  });

  it("formats numbers without trailing zeros", () => {
    expect(formatNumber("1500.0000")).toBe("1,500");
    expect(formatNumber("228.402000")).toBe("228.402");
  });

  it("formats percentages", () => {
    expect(formatPercent("75.61")).toBe("75.61%");
    expect(formatPercent(null)).toBe("-");
  });

  it("formats ISO dates without timezone drift", () => {
    expect(formatDate("2026-10-14")).toBe("14 Oct 2026");
    expect(formatDate("")).toBe("-");
  });

  it("humanizes enum values", () => {
    expect(humanize("MISSING_IN_CUSTODIAN")).toBe("Missing In Custodian");
  });
});

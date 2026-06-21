import { describe, it, expect } from "vitest";
import { uptimeColor } from "./colors";

describe("uptimeColor", () => {
  it("returns gray for negative (no data)", () => {
    expect(uptimeColor(-1)).toBe("#e5e7eb");
  });

  it("returns red for 0%", () => {
    expect(uptimeColor(0)).toBe("hsl(0, 85%, 40%)");
  });

  it("returns red for 50%", () => {
    expect(uptimeColor(0.5)).toBe("hsl(0, 85%, 40%)");
  });

  it("returns red for 89.9%", () => {
    expect(uptimeColor(0.899)).toBe("hsl(0, 85%, 40%)");
  });

  it("returns amber start for 90%", () => {
    expect(uptimeColor(0.9)).toBe("hsl(45, 85%, 40%)");
  });

  it("returns green for 99.9%", () => {
    expect(uptimeColor(0.999)).toBe("hsl(120, 85%, 40%)");
  });

  it("returns green for 100%", () => {
    expect(uptimeColor(1)).toBe("hsl(120, 85%, 40%)");
  });
});

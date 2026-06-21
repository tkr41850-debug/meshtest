import { describe, it, expect } from "vitest";
import { barColor, renderBars } from "./bars";

describe("barColor", () => {
  it("returns gray for negative (no data)", () => {
    expect(barColor(-1)).toBe("#e5e7eb");
  });

  it("returns red for 0%", () => {
    expect(barColor(0)).toBe("hsl(0, 85%, 40%)");
  });

  it("returns red for 50% (below 90% threshold)", () => {
    expect(barColor(0.5)).toBe("hsl(0, 85%, 40%)");
  });

  it("returns red for 90% (start of red~amber ramp)", () => {
    expect(barColor(0.9)).toBe("hsl(0, 85%, 40%)");
  });

  it("returns amber for 99%", () => {
    expect(barColor(0.99)).toBe("hsl(45, 85%, 40%)");
  });

  it("returns green for 100%", () => {
    expect(barColor(1)).toBe("hsl(120, 85%, 40%)");
  });
});

describe("renderBars", () => {
  it("renders correct number of bars", () => {
    const bars = [
      { percent: 1, tooltip: "100%" },
      { percent: 0, tooltip: "0%" },
    ];
    const html = renderBars(bars);
    const div = document.createElement("div");
    div.innerHTML = html;
    expect(div.querySelectorAll("[data-history-bar]").length).toBe(2);
  });

  it("renders bars with data-tooltip instead of title", () => {
    const bars = [
      { percent: -1, tooltip: "" },
      { percent: 0.5, tooltip: "50%" },
    ];
    const html = renderBars(bars);
    const div = document.createElement("div");
    div.innerHTML = html;
    const allBars = div.querySelectorAll("[data-history-bar]");
    expect(allBars[0].hasAttribute("title")).toBe(false);
    expect(allBars[0].getAttribute("data-tooltip")).toBe("No data");
    expect(allBars[1].hasAttribute("title")).toBe(false);
    expect(allBars[1].getAttribute("data-tooltip")).toBe("50%");
  });

  it("renders inline-block spans with width 8px", () => {
    const bars = [{ percent: 1, tooltip: "full" }];
    const html = renderBars(bars);
    expect(html).toContain("width:8px");
    expect(html).toContain("height:20px");
    expect(html).toContain("border-radius:1px");
  });
});

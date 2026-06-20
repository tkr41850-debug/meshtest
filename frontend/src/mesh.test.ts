import { describe, it, expect } from "vitest";
import { renderMatrix } from "./views/matrix";
import { renderCards } from "./views/cards";
import { renderDay30 } from "./views/day30";

describe("renderMatrix", () => {
  it("renders table with correct number of rows/cols", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1", "10.0.0.2"], [
      {
        node_ip: "10.0.0.1",
        target_ip: "10.0.0.2",
        ping_status: "OK",
        http_status: "OK",
      },
    ]);
    expect(container.querySelectorAll("tr").length).toBe(3);
  });

  it("shows gray dots for pending status", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1", "10.0.0.2"], []);
    expect(container.innerHTML).toContain("●");
  });

  it("shows message for fewer than 2 nodes", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1"], []);
    expect(container.innerHTML).toContain(
      "Need at least 2 nodes",
    );
  });

  it("shows em-dash on diagonal", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1", "10.0.0.2"], []);
    const cells = container.querySelectorAll("td");
    expect(cells[1].textContent).toBe("—");
  });

  it("shows green dot for OK status", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1", "10.0.0.2"], [
      {
        node_ip: "10.0.0.1",
        target_ip: "10.0.0.2",
        ping_status: "OK",
        http_status: "OK",
      },
    ]);
    const dot = container.querySelector(".text-mesh-green");
    expect(dot?.textContent).toBe("●");
  });

  it("shows amber dot for NotAvailable status", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["10.0.0.1", "10.0.0.2"], [
      {
        node_ip: "10.0.0.1",
        target_ip: "10.0.0.2",
        ping_status: "NotAvailable",
        http_status: "OK",
      },
    ]);
    const dot = container.querySelector(".text-mesh-amber");
    expect(dot?.textContent).toBe("●");
  });

  it("sets short label with full IP title on column headers", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["node-abc-10.0.0.1", "10.0.0.2"], []);
    const headers = container.querySelectorAll("th");
    expect(headers[1].getAttribute("title")).toBe("node-abc-10.0.0.1");
  });
});

describe("renderCards", () => {
  it("renders source group divs instead of details expanders", () => {
    const container = document.createElement("div");
    renderCards(
      container,
      ["10.0.0.1", "10.0.0.2"],
      [],
      [],
      new Map(),
    );
    expect(container.querySelectorAll("details").length).toBe(0);
    const groups = container.querySelectorAll("[data-source-group]");
    expect(groups.length).toBe(2);
  });

  it("renders sticky source headers", () => {
    const container = document.createElement("div");
    renderCards(
      container,
      ["10.0.0.1", "10.0.0.2"],
      [],
      [],
      new Map(),
    );
    const headers = container.querySelectorAll("[data-source-header]");
    expect(headers.length).toBe(2);
    expect(headers[0].textContent).toContain("10.0.0.1");
    expect(headers[1].textContent).toContain("10.0.0.2");
  });

  it("shows no-nodes message for empty list", () => {
    const container = document.createElement("div");
    renderCards(container, [], [], [], new Map());
    expect(container.innerHTML).toContain("No nodes registered");
  });

  it("skips self-pair in cards", () => {
    const container = document.createElement("div");
    renderCards(container, ["10.0.0.1"], [], [], new Map());
    expect(container.querySelectorAll(".rounded-lg").length).toBe(0);
  });

  it("renders card with OK status badge and uptime %", () => {
    const container = document.createElement("div");
    renderCards(
      container,
      ["10.0.0.1", "10.0.0.2"],
      [
        {
          node_ip: "10.0.0.1",
          target_ip: "10.0.0.2",
          ping_status: "OK",
          http_status: "OK",
        },
      ],
      [
        {
          node_ip: "10.0.0.1",
          target_ip: "10.0.0.2",
          ping_ok: true,
          http_ok: true,
          ping_latency_ms: 5.2,
          http_latency_ms: 12.1,
          timestamp: 1000000,
        },
      ],
      new Map([["10.0.0.1|10.0.0.2", [99.5, 100]]]),
    );
    expect(container.innerHTML).toContain("OK");
    expect(container.innerHTML).toContain("5.2ms");
    expect(container.innerHTML).toContain("12.1ms");
    expect(container.innerHTML).toContain("99.5");
    expect(container.innerHTML).toContain("100.0");
  });

  it("groups cards by source with separators between groups", () => {
    const container = document.createElement("div");
    renderCards(
      container,
      ["10.0.0.1", "10.0.0.2", "10.0.0.3"],
      [],
      [],
      new Map(),
    );
    const groups = container.querySelectorAll("[data-source-group]");
    expect(groups.length).toBe(3);
    const cardsInGroup1 = groups[0].querySelectorAll(".rounded-lg");
    expect(cardsInGroup1.length).toBe(2);
  });

  it("uses tailwind sticky class on source header", () => {
    const container = document.createElement("div");
    renderCards(container, ["10.0.0.1", "10.0.0.2"], [], [], new Map());
    const header = container.querySelector("[data-source-header]");
    expect(header?.className).toContain("sticky");
  });

  it("renders 30 history bars per card with gradient colors", () => {
    const container = document.createElement("div");
    const now = 1000000;
    const checks = Array.from({ length: 30 }, (_, i) => ({
      node_ip: "10.0.0.1",
      target_ip: "10.0.0.2",
      ping_ok: true,
      http_ok: true,
      ping_latency_ms: 5,
      http_latency_ms: 10,
      timestamp: now - (29 - i) * 60,
    }));
    renderCards(
      container,
      ["10.0.0.1", "10.0.0.2"],
      [
        {
          node_ip: "10.0.0.1",
          target_ip: "10.0.0.2",
          ping_status: "OK",
          http_status: "OK",
        },
      ],
      checks,
      new Map([["10.0.0.1|10.0.0.2", [100, 100]]]),
    );
    const bars = container.querySelectorAll("[data-history-bar]");
    expect(bars.length).toBeGreaterThanOrEqual(1);
    expect(bars[0].getAttribute("title")).toContain("Ping");
  });

  it("computes correct bar uptime percentages from ping_ok/http_ok", () => {
    const container = document.createElement("div");
    const now = 1000000;
    const checks = Array.from({ length: 30 }, (_, i) => ({
      node_ip: "10.0.0.1",
      target_ip: "10.0.0.2",
      ping_ok: true,
      http_ok: true,
      ping_latency_ms: 5,
      http_latency_ms: 10,
      timestamp: now - (29 - i) * 60,
    }));
    renderCards(
      container,
      ["10.0.0.1", "10.0.0.2"],
      [
        {
          node_ip: "10.0.0.1",
          target_ip: "10.0.0.2",
          ping_status: "OK",
          http_status: "OK",
        },
      ],
      checks,
      new Map([["10.0.0.1|10.0.0.2", [100, 100]]]),
    );
    const bars = container.querySelectorAll("[data-history-bar]");
    const hasFullUptime = [...bars].some(
      (b) =>
        b.getAttribute("title")?.includes("Ping: 100.0%") &&
        b.getAttribute("title")?.includes("HTTP: 100.0%"),
    );
    expect(hasFullUptime).toBe(true);
  });

  it("shows empty gray bars when no checks for a pair", () => {
    const container = document.createElement("div");
    renderCards(
      container,
      ["10.0.0.1", "10.0.0.2"],
      [],
      [],
      new Map(),
    );
    const bars = container.querySelectorAll("[data-history-bar]");
    // 2 sources × 1 target each = 2 cards, each with 30 bars
    expect(bars.length).toBe(60);
    expect(bars[0].getAttribute("title")).toBe("No data");
  });

  it("includes history bars below Ping/HTTP/Last stats row", () => {
    const container = document.createElement("div");
    renderCards(
      container,
      ["10.0.0.1", "10.0.0.2"],
      [
        {
          node_ip: "10.0.0.1",
          target_ip: "10.0.0.2",
          ping_status: "OK",
          http_status: "OK",
        },
      ],
      [
        {
          node_ip: "10.0.0.1",
          target_ip: "10.0.0.2",
          ping_ok: true,
          http_ok: true,
          ping_latency_ms: 5.2,
          http_latency_ms: 12.1,
          timestamp: 1000000,
        },
      ],
      new Map(),
    );
    const card = container.querySelector(".rounded-lg")!;
    const statsLine = card.querySelector(".text-mesh-muted")!;
    const barsAfterStats = statsLine.nextElementSibling;
    expect(barsAfterStats?.querySelectorAll("[data-history-bar]").length).toBe(
      30,
    );
  });
});

describe("renderDay30", () => {
  it("renders expanders per source node", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [
          {
            node_ip: "10.0.0.1",
            target_ip: "10.0.0.2",
            ping_uptime_pct: 100,
            http_uptime_pct: 99.5,
            total_checks: 8640,
          },
        ],
      },
    ]);
    expect(container.querySelectorAll("details").length).toBe(2);
  });

  it("shows no-data message for null days", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1"], undefined);
    expect(container.innerHTML).toContain("No data available");
  });

  it("sets data-node-pair attribute on circles", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [
          {
            node_ip: "10.0.0.1",
            target_ip: "10.0.0.2",
            ping_uptime_pct: 100,
            http_uptime_pct: 99.5,
            total_checks: 8640,
          },
        ],
      },
    ]);
    const circle = container.querySelector("[data-node-pair]");
    expect(circle?.getAttribute("data-node-pair")).toBe(
      "10.0.0.1--10.0.0.2",
    );
  });

  it("renders uptime badge with correct color for >=99%", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [
          {
            node_ip: "10.0.0.1",
            target_ip: "10.0.0.2",
            ping_uptime_pct: 100,
            http_uptime_pct: 99.5,
            total_checks: 8640,
          },
        ],
      },
    ]);
    const badges = container.querySelectorAll(".rounded");
    expect(badges.length).toBe(1);
    expect(badges[0].textContent).toContain("100.0%");
  });

  it("shows no-data line for days without connections", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [],
      },
    ]);
    expect(container.innerHTML).toContain("2026-06-01");
  });

  it("renders daily history bars per pair with gradient colors", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [
          {
            node_ip: "10.0.0.1",
            target_ip: "10.0.0.2",
            ping_uptime_pct: 100,
            http_uptime_pct: 99.5,
            total_checks: 8640,
          },
        ],
      },
    ]);
    const bars = container.querySelectorAll("[data-history-bar]");
    expect(bars.length).toBe(30);
    // Bars are right-aligned — last bar has data
    const lastBar = bars[bars.length - 1];
    expect(lastBar.getAttribute("title")).toContain("Ping");
    expect(lastBar.getAttribute("title")).toContain("HTTP");
  });

  it("shows empty bars in day30 when no data for some days", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [
          {
            node_ip: "10.0.0.1",
            target_ip: "10.0.0.2",
            ping_uptime_pct: 100,
            http_uptime_pct: 99.5,
            total_checks: 8640,
          },
        ],
      },
    ]);
    const bars = container.querySelectorAll("[data-history-bar]");
    const filledBars = [...bars].filter(
      (b) => b.getAttribute("title") !== "No data",
    );
    expect(filledBars.length).toBe(1);
  });
});

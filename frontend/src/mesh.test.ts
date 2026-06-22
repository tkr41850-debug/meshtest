import { describe, it, expect } from "vitest";
import { renderMatrix } from "./views/matrix";
import { renderCards } from "./views/cards";
import { renderDay30 } from "./views/day30";
import { renderHourly } from "./views/hourly";

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

  it("sets short label with full IP tooltip on column headers", () => {
    const container = document.createElement("div");
    renderMatrix(container, ["node-abc-10.0.0.1", "10.0.0.2"], []);
    const headers = container.querySelectorAll("th");
    const tooltip = headers[1].querySelector(".mesh-tooltip");
    expect(tooltip?.textContent).toBe("node-abc-10.0.0.1");
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

  it("renders dual ICMP/HTTP history bar rows per card", () => {
    const container = document.createElement("div");
    const now = 1000000;
    const checks = Array.from({ length: 90 }, (_, i) => ({
      node_ip: "10.0.0.1",
      target_ip: "10.0.0.2",
      ping_ok: true,
      http_ok: true,
      ping_latency_ms: 5,
      http_latency_ms: 10,
      timestamp: now - (89 - i) * 60,
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
    expect(bars.length).toBe(360);
    const tooltips = container.querySelectorAll(".mesh-tooltip");
    expect(tooltips.length).toBe(360);
    expect(tooltips[0]?.textContent).toMatch(/100\.0% ICMP/);
    expect(tooltips[90]?.textContent).toMatch(/100\.0% HTTP/);
  });

  it("computes correct bar uptime percentages from ping_ok/http_ok", () => {
    const container = document.createElement("div");
    const now = 1000000;
    const checks = Array.from({ length: 90 }, (_, i) => ({
      node_ip: "10.0.0.1",
      target_ip: "10.0.0.2",
      ping_ok: true,
      http_ok: true,
      ping_latency_ms: 5,
      http_latency_ms: 10,
      timestamp: now - (89 - i) * 60,
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
    const hasIcmp100 = [...bars].some(
      (b) => b.getAttribute("data-tooltip")?.includes("100.0% ICMP"),
    );
    const hasHttp100 = [...bars].some(
      (b) => b.getAttribute("data-tooltip")?.includes("100.0% HTTP"),
    );
    expect(hasIcmp100).toBe(true);
    expect(hasHttp100).toBe(true);
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
    expect(bars.length).toBe(360);
    expect(bars[0].getAttribute("data-tooltip")).toBe("No data");
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
      90,
    );
  });
});

describe("renderDay30", () => {
  it("renders source group divs instead of details expanders", () => {
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
            ping_ok: 8640,
            http_ok: 8597,
          },
        ],
      },
    ]);
    expect(container.querySelectorAll("details").length).toBe(0);
    const groups = container.querySelectorAll("[data-source-group]");
    expect(groups.length).toBe(2);
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
            ping_ok: 8640,
            http_ok: 8597,
          },
        ],
      },
    ]);
    const circle = container.querySelector("[data-node-pair]");
    expect(circle?.getAttribute("data-node-pair")).toBe(
      "10.0.0.1--10.0.0.2",
    );
  });

  it("renders status badge and uptime for >=99%", () => {
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
            ping_ok: 8640,
            http_ok: 8597,
          },
        ],
      },
    ]);
    expect(container.innerHTML).toContain("100.0%");
    expect(container.innerHTML).toContain("99.5%");
  });

  it("shows no-data message for day without connections", () => {
    const container = document.createElement("div");
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], [
      {
        date: "2026-06-01",
        connections: [],
      },
    ]);
    expect(container.innerHTML).toContain("No data for this node");
  });

  it("renders daily ICMP/HTTP bar rows per pair", () => {
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
            ping_ok: 8640,
            http_ok: 8597,
          },
        ],
      },
    ]);
    const bars = container.querySelectorAll("[data-history-bar]");
    expect(bars.length).toBe(180);
    const tooltips = container.querySelectorAll(".mesh-tooltip");
    expect(tooltips.length).toBe(180);
    expect(tooltips[89]?.textContent).toMatch(/2026-06-01.*100\.0% ICMP/);
    expect(tooltips[179]?.textContent).toMatch(/2026-06-01.*99\.5% HTTP/);
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
            ping_ok: 8640,
            http_ok: 8597,
          },
        ],
      },
    ]);
    const bars = container.querySelectorAll("[data-history-bar]");
    const filledBars = [...bars].filter(
      (b) => b.getAttribute("data-tooltip") !== "No data",
    );
    expect(filledBars.length).toBe(2);
  });

  it("sums total_checks across multiple days", () => {
    const container = document.createElement("div");
    const days = [
      {
        date: "2026-06-01",
        connections: [
          { node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 100, http_uptime_pct: 100, total_checks: 10, ping_ok: 10, http_ok: 10 },
        ],
      },
      {
        date: "2026-06-02",
        connections: [
          { node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 99.5, http_uptime_pct: 100, total_checks: 20, ping_ok: 20, http_ok: 20 },
        ],
      },
      {
        date: "2026-06-03",
        connections: [
          { node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 100, http_uptime_pct: 99.9, total_checks: 30, ping_ok: 30, http_ok: 30 },
        ],
      },
    ];
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], days);
    expect(container.innerHTML).toContain('Checks: <strong class="text-mesh-dark">60</strong>');
  });

  it("displays aggregate pct across days instead of first-day value", () => {
    const container = document.createElement("div");
    const days = [
      { date: "2026-06-01", connections: [{ node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 100, http_uptime_pct: 100, total_checks: 100, ping_ok: 100, http_ok: 100 }] },
      { date: "2026-06-02", connections: [{ node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 83.3, http_uptime_pct: 83.3, total_checks: 6, ping_ok: 5, http_ok: 5 }] },
    ];
    renderDay30(container, ["10.0.0.1", "10.0.0.2"], days);
    expect(container.innerHTML).toContain("99.1%");
    expect(container.innerHTML).toContain("106");
  });
});

describe("renderHourly", () => {
  it("shows no-data message for undefined hours", () => {
    const container = document.createElement("div");
    renderHourly(container, ["10.0.0.1"], undefined);
    expect(container.innerHTML).toContain("No data available");
  });

  it("shows no-data message for empty hours", () => {
    const container = document.createElement("div");
    renderHourly(container, ["10.0.0.1"], []);
    expect(container.innerHTML).toContain("No data available");
  });

  it("renders cards for pairs with hourly data", () => {
    const container = document.createElement("div");
    const hours = [
      {
        date: "2026-06-01T14:00",
        connections: [
          { node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 100, http_uptime_pct: 100, total_checks: 100, ping_ok: 100, http_ok: 100 },
        ],
      },
    ];
    renderHourly(container, ["10.0.0.1", "10.0.0.2"], hours);
    const cards = container.querySelectorAll(".rounded-lg");
    expect(cards.length).toBe(1);
    expect(cards[0].textContent).toContain("10.0.0.2");
  });

  it("sums total_checks across multiple hours", () => {
    const container = document.createElement("div");
    const hours = [
      {
        date: "2026-06-01T14:00",
        connections: [
          { node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 100, http_uptime_pct: 100, total_checks: 100, ping_ok: 100, http_ok: 100 },
        ],
      },
      {
        date: "2026-06-01T15:00",
        connections: [
          { node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 99.5, http_uptime_pct: 100, total_checks: 120, ping_ok: 119, http_ok: 120 },
        ],
      },
      {
        date: "2026-06-01T16:00",
        connections: [
          { node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 100, http_uptime_pct: 99.9, total_checks: 140, ping_ok: 140, http_ok: 140 },
        ],
      },
    ];
    renderHourly(container, ["10.0.0.1", "10.0.0.2"], hours);
    expect(container.innerHTML).toContain('Checks: <strong class="text-mesh-dark">360</strong>');
  });

  it("displays aggregate pct across hours instead of first-hour value", () => {
    const container = document.createElement("div");
    const hours = [
      { date: "2026-06-01T10:00", connections: [{ node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 100, http_uptime_pct: 100, total_checks: 100, ping_ok: 100, http_ok: 100 }] },
      { date: "2026-06-01T11:00", connections: [{ node_ip: "10.0.0.1", target_ip: "10.0.0.2", ping_uptime_pct: 83.3, http_uptime_pct: 83.3, total_checks: 6, ping_ok: 5, http_ok: 5 }] },
    ];
    renderHourly(container, ["10.0.0.1", "10.0.0.2"], hours);
    expect(container.innerHTML).toContain("99.1%");
    expect(container.innerHTML).toContain("106");
  });

  it("shows no-data message when source has no pairs", () => {
    const container = document.createElement("div");
    const hours = [
      {
        date: "2026-06-01T14:00",
        connections: [
          { node_ip: "10.0.0.3", target_ip: "10.0.0.4", ping_uptime_pct: 100, http_uptime_pct: 100, total_checks: 10, ping_ok: 10, http_ok: 10 },
        ],
      },
    ];
    renderHourly(container, ["10.0.0.1", "10.0.0.2"], hours);
    expect(container.innerHTML).toContain("No data for this node");
  });
});

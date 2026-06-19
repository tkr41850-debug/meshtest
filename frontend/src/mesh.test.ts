import { describe, it, expect } from "vitest";
import { renderMatrix } from "./views/matrix";
import { renderCards } from "./views/cards";
import { renderDay30 } from "./views/day30";
import { renderHistory } from "./views/history";

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
  it("renders expanders per source node", () => {
    const container = document.createElement("div");
    renderCards(
      container,
      ["10.0.0.1", "10.0.0.2"],
      [],
      [],
      new Map(),
    );
    expect(container.querySelectorAll("details").length).toBe(2);
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

  it("renders card with OK status badge", () => {
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
          ping_status: "OK",
          http_status: "OK",
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
});

describe("renderHistory", () => {
  it("renders source node expanders", () => {
    const container = document.createElement("div");
    renderHistory(container, ["10.0.0.1", "10.0.0.2"], [
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
    expect(container.querySelectorAll("details").length).toBeGreaterThan(
      0,
    );
  });

  it("shows no-data message for undefined days", () => {
    const container = document.createElement("div");
    renderHistory(container, ["10.0.0.1"], undefined);
    expect(container.innerHTML).toContain("No history data");
  });

  it("renders bars with gradient for connection data", () => {
    const container = document.createElement("div");
    renderHistory(container, ["10.0.0.1", "10.0.0.2"], [
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
    expect(container.innerHTML).toContain(
      "background:linear-gradient",
    );
    expect(container.innerHTML).toContain("svg");
  });

  it("sets history section id for scrollTo", () => {
    const container = document.createElement("div");
    renderHistory(container, ["10.0.0.1", "10.0.0.2"], [
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
    expect(container.innerHTML).toContain(
      'id="history-10.0.0.1--10.0.0.2"',
    );
  });

  it("shows empty bars when there is less than 30 days of data", () => {
    const container = document.createElement("div");
    renderHistory(container, ["10.0.0.1", "10.0.0.2"], [
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
    expect(container.innerHTML).toContain("No data");
  });
});

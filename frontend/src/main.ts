import "./style.css";
import { fetchData90m, fetchData90h, fetchData90d, fetchNodeList } from "./api";
import { renderMatrix } from "./views/matrix";
import { renderCards } from "./views/cards";
import { renderDay30 } from "./views/day30";
import { renderHourly } from "./views/hourly";

const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
  <div class="max-w-6xl mx-auto p-6">
    <h1 class="text-2xl font-bold text-mesh-dark mb-4">mesh-status</h1>
    <div class="flex gap-2 mb-4 border-b border-mesh-border">
      <button id="tab-90m" class="tab-btn px-4 py-2 text-sm font-semibold text-mesh-dark border-b-2 border-mesh-green">90-Minute View</button>
      <button id="tab-90h" class="tab-btn px-4 py-2 text-sm font-semibold text-mesh-muted border-b-2 border-transparent">90-Hour View</button>
      <button id="tab-90d" class="tab-btn px-4 py-2 text-sm font-semibold text-mesh-muted border-b-2 border-transparent">90-Day View</button>
    </div>
    <div id="matrix-container" class="mb-6"></div>
    <div id="cards-container"></div>
    <div id="hourly-container" class="hidden"></div>
    <div id="day90-container" class="hidden"></div>
    <p id="refresh-indicator" class="text-center text-xs text-mesh-muted mt-6">Loading mesh data...</p>
  </div>
`;

const matrixContainer = document.querySelector<HTMLDivElement>("#matrix-container")!;
const cardsContainer = document.querySelector<HTMLDivElement>("#cards-container")!;
const hourlyContainer = document.querySelector<HTMLDivElement>("#hourly-container")!;
const day90Container = document.querySelector<HTMLDivElement>("#day90-container")!;
const indicator = document.querySelector<HTMLParagraphElement>("#refresh-indicator")!;
const tab90m = document.querySelector<HTMLButtonElement>("#tab-90m")!;
const tab90h = document.querySelector<HTMLButtonElement>("#tab-90h")!;
const tab90d = document.querySelector<HTMLButtonElement>("#tab-90d")!;

function resetTabStyles(): void {
  const inactive =
    "tab-btn px-4 py-2 text-sm font-semibold text-mesh-muted border-b-2 border-transparent";
  tab90m.className = inactive;
  tab90h.className = inactive;
  tab90d.className = inactive;
}

function switchTab(tab: "90m" | "90h" | "90d"): void {
  resetTabStyles();
  matrixContainer.classList.add("hidden");
  cardsContainer.classList.add("hidden");
  hourlyContainer.classList.add("hidden");
  day90Container.classList.add("hidden");

  const active =
    "tab-btn px-4 py-2 text-sm font-semibold text-mesh-dark border-b-2 border-mesh-green";
  if (tab === "90m") {
    matrixContainer.classList.remove("hidden");
    cardsContainer.classList.remove("hidden");
    tab90m.className = active;
  } else if (tab === "90h") {
    hourlyContainer.classList.remove("hidden");
    tab90h.className = active;
  } else {
    day90Container.classList.remove("hidden");
    tab90d.className = active;
  }
}

tab90m.addEventListener("click", () => switchTab("90m"));
tab90h.addEventListener("click", () => switchTab("90h"));
tab90d.addEventListener("click", () => switchTab("90d"));

function buildUptimeMap(
  data90d: Awaited<ReturnType<typeof fetchData90d>>,
): Map<string, [number | null, number | null]> {
  const map = new Map<string, [number | null, number | null]>();
  if (!data90d?.days) return map;
  for (const day of data90d.days) {
    for (const conn of day.connections) {
      map.set(`${conn.node_ip}|${conn.target_ip}`, [
        conn.ping_uptime_pct,
        conn.http_uptime_pct,
      ]);
    }
  }
  return map;
}

async function refresh(): Promise<void> {
  const [data90m, data90h, data90d, nodeList] = await Promise.all([
    fetchData90m(),
    fetchData90h(),
    fetchData90d(),
    fetchNodeList(),
  ]);

  const nodes =
    nodeList?.nodes?.map((n) =>
      typeof n === "string" ? n : n.ip,
    ) ?? [];

  if (!data90m) {
    indicator.textContent =
      "⚠ Leader unreachable — showing cached data";
  } else {
    indicator.textContent = `🔄 Auto-refreshing every 10s | Last update: ${new Date().toLocaleTimeString()}`;
  }

  const statuses = data90m?.statuses ?? [];
  const checks = data90m?.checks ?? [];
  const uptimeMap = buildUptimeMap(data90d);

  if (nodes.length === 0) {
    matrixContainer.innerHTML =
      '<p class="text-mesh-muted text-sm">No nodes registered</p>';
    cardsContainer.innerHTML =
      '<p class="text-mesh-muted text-sm">No nodes registered</p>';
  } else {
    renderMatrix(matrixContainer, nodes, statuses);
    renderCards(cardsContainer, nodes, statuses, checks, uptimeMap);
  }

  renderHourly(hourlyContainer, nodes, data90h?.hours);
  renderDay30(day90Container, nodes, data90d?.days);
}

refresh();
setInterval(refresh, 10_000);

// ScrollTo from day/hour views to 90m cards
day90Container.addEventListener("click", (e) => {
  const target = e.target as HTMLElement;
  const cell = target.closest("[data-node-pair]");
  if (cell) {
    const pairKey = cell.getAttribute("data-node-pair");
    if (pairKey) {
      switchTab("90m");
      const [src] = pairKey.split("--");
      const headers = document.querySelectorAll("[data-source-header]");
      for (const h of headers) {
        if (h.textContent?.includes(src)) {
          h.scrollIntoView({ behavior: "smooth" });
          break;
        }
      }
    }
  }
});

hourlyContainer.addEventListener("click", (e) => {
  const target = e.target as HTMLElement;
  const cell = target.closest("[data-node-pair]");
  if (cell) {
    const pairKey = cell.getAttribute("data-node-pair");
    if (pairKey) {
      switchTab("90m");
      const [src] = pairKey.split("--");
      const headers = document.querySelectorAll("[data-source-header]");
      for (const h of headers) {
        if (h.textContent?.includes(src)) {
          h.scrollIntoView({ behavior: "smooth" });
          break;
        }
      }
    }
  }
});

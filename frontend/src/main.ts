import "./style.css";
import { fetchData30m, fetchData30d, fetchNodeList } from "./api";
import { renderMatrix } from "./views/matrix";
import { renderCards } from "./views/cards";
import { renderDay30 } from "./views/day30";

const app = document.querySelector<HTMLDivElement>("#app")!;
app.innerHTML = `
  <div class="max-w-6xl mx-auto p-6">
    <h1 class="text-2xl font-bold text-mesh-dark mb-4">mesh-status</h1>
    <div class="flex gap-2 mb-4 border-b border-mesh-border">
      <button id="tab-30m" class="tab-btn px-4 py-2 text-sm font-semibold text-mesh-dark border-b-2 border-mesh-green">30-Minute View</button>
      <button id="tab-30d" class="tab-btn px-4 py-2 text-sm font-semibold text-mesh-muted border-b-2 border-transparent">30-Day View</button>
    </div>
    <div id="matrix-container"></div>
    <div id="cards-container"></div>
    <div id="day30-container" class="hidden"></div>
    <p id="refresh-indicator" class="text-center text-xs text-mesh-muted mt-6">Loading mesh data...</p>
  </div>
`;

const matrixContainer = document.querySelector<HTMLDivElement>("#matrix-container")!;
const cardsContainer = document.querySelector<HTMLDivElement>("#cards-container")!;
const day30Container = document.querySelector<HTMLDivElement>("#day30-container")!;
const indicator = document.querySelector<HTMLParagraphElement>("#refresh-indicator")!;
const tab30m = document.querySelector<HTMLButtonElement>("#tab-30m")!;
const tab30d = document.querySelector<HTMLButtonElement>("#tab-30d")!;

function switchTab(tab: "30m" | "30d"): void {
  const is30m = tab === "30m";
  matrixContainer.classList.toggle("hidden", !is30m);
  cardsContainer.classList.toggle("hidden", !is30m);
  day30Container.classList.toggle("hidden", is30m);
  tab30m.className = is30m
    ? "tab-btn px-4 py-2 text-sm font-semibold text-mesh-dark border-b-2 border-mesh-green"
    : "tab-btn px-4 py-2 text-sm font-semibold text-mesh-muted border-b-2 border-transparent";
  tab30d.className = is30m
    ? "tab-btn px-4 py-2 text-sm font-semibold text-mesh-muted border-b-2 border-transparent"
    : "tab-btn px-4 py-2 text-sm font-semibold text-mesh-dark border-b-2 border-mesh-green";
}

tab30m.addEventListener("click", () => switchTab("30m"));
tab30d.addEventListener("click", () => switchTab("30d"));

function buildUptimeMap(
  data30d: Awaited<ReturnType<typeof fetchData30d>>,
): Map<string, [number | null, number | null]> {
  const map = new Map<string, [number | null, number | null]>();
  if (!data30d?.days) return map;
  for (const day of data30d.days) {
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
  const [data30m, data30d, nodeList] = await Promise.all([
    fetchData30m(),
    fetchData30d(),
    fetchNodeList(),
  ]);

  const nodes =
    nodeList?.nodes?.map((n) =>
      typeof n === "string" ? n : n.ip,
    ) ?? [];

  if (!data30m) {
    indicator.textContent =
      "⚠ Leader unreachable — showing cached data";
  } else {
    indicator.textContent = `🔄 Auto-refreshing every 10s | Last update: ${new Date().toLocaleTimeString()}`;
  }

  const statuses = data30m?.statuses ?? [];
  const checks = data30m?.checks ?? [];
  const uptimeMap = buildUptimeMap(data30d);

  if (nodes.length === 0) {
    matrixContainer.innerHTML =
      '<p class="text-mesh-muted text-sm">No nodes registered</p>';
    cardsContainer.innerHTML =
      '<p class="text-mesh-muted text-sm">No nodes registered</p>';
  } else {
    renderMatrix(matrixContainer, nodes, statuses);
    renderCards(cardsContainer, nodes, statuses, checks, uptimeMap);
  }

  renderDay30(day30Container, nodes, data30d?.days);
}

refresh();
setInterval(refresh, 10_000);

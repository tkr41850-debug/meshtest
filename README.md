# mesh-status

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN.

## Quick Start (Docker)

**Prerequisites:** Docker and Docker Compose.

```bash
# Clone and start
docker compose up -d

# Check leader health
curl http://localhost:58080/livez

# Open dashboard
open http://localhost:58581
```

Data is persisted in `./data/` on the host.

## Single-Architecture Builds

Build for the current platform:

```bash
# Leader
docker build -f Dockerfile.leader -t mesh-leader .

# Node
docker build -f Dockerfile.node -t mesh-node .
```

## Multi-Architecture Builds

Build for both `linux/amd64` and `linux/arm64`:

```bash
# Ensure buildx is available
docker buildx create --use 2>/dev/null || true

# Leader
docker buildx build --platform linux/amd64,linux/arm64 \
  -t mesh-leader -f Dockerfile.leader --load .

# Node
docker buildx build --platform linux/amd64,linux/arm64 \
  -t mesh-node -f Dockerfile.node --load .
```

Note: `--load` saves only the current architecture locally. Use `--push` to push a multi-arch manifest to a registry.

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LEADER_URL` | `http://localhost:58080` | URL of the leader's HTTP API (for dashboard) |
| `LEADER_HOST` | `0.0.0.0` | Leader bind address |
| `LEADER_PORT` | `58080` | Leader API port |
| `DATA_DIR` | `/app/data` | Data persistence directory |
| `MESH_STATUS_PORT` | `58080` | Node HTTP server port |
| `MESH_STATUS_INTERVAL` | `10` | Check interval in seconds |
| `LEADER_IP` | `leader` | Leader hostname (node connects to this) |
| `NODE_IP` | (auto-detect) | IP the node advertises to the leader |

### Ports

| Port | Service | Description |
|------|---------|-------------|
| 58080 | Leader API | Quart HTTP server (Hypercorn) |
| 58581 | Dashboard | Streamlit UI |
| 58081 | Node API | Per-node HTTP server (aiohttp) |

## Manual Setup (without Docker)

### Prerequisites

- Python 3.12+
- `uv` (recommended) or `pip`

```bash
# Install with uv
uv sync --no-dev

# Or with pip
pip install -e .
```

### Run Components

```bash
# Leader
hypercorn mesh_status.leader:app --bind 0.0.0.0:58080

# Node
uv run python node.py --leader-ip <leader-ip> --node-ip <this-node-ip>

# Dashboard
LEADER_URL=http://<leader-ip>:58080 streamlit run mesh_status/dashboard.py --server.port 58581
```

Open `http://localhost:58581` (or the host IP) in a browser.

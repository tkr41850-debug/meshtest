# mesh-status

[![Build & Push Docker Images](https://github.com/tkr41850-debug/meshtest/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/tkr41850-debug/meshtest/actions/workflows/docker-publish.yml)

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN.

## Quick Start (Docker)

**Prerequisites:** Docker and Docker Compose.

```bash
# Clone and start
docker compose up -d --pull=always

# Check leader health
curl http://localhost:58080/livez

# Open dashboard
open http://localhost:58581
```

Data is persisted in `./data/` on the host.

## Docker Images

Pre-built multi-arch images are available on Docker Hub:

| Image | Description |
|-------|-------------|
| `tkr41850/mesh-leader` | Leader + Dashboard |
| `tkr41850/mesh-node` | Node agent |

### Run Pre-built Images

**Leader (with Dashboard):**

```bash
docker run -d --pull=always --restart unless-stopped \
  --name mesh-leader \
  -p 58080:58080 \
  -p 58581:58581 \
  -v ./data:/app/data \
  -e LEADER_URL=http://localhost:58080 \
  tkr41850/mesh-leader
```

**Node agent (same machine):**

```bash
docker run -d --pull=always --restart unless-stopped \
  --name mesh-node1 \
  -p 58081:58081 \
  -e LEADER_URL=http://localhost:58080 \
  -e NODE_URL=http://localhost:58081 \
  -e MESH_STATUS_INTERVAL=10 \
  tkr41850/mesh-node
```

**Node agent (different machine — cross-VM):**

```bash
docker run -d --pull=always --restart unless-stopped \
  --name mesh-node1 \
  -p 58081:58081 \
  -e LEADER_URL=http://<leader-url>:58080 \
  -e NODE_URL=http://<node-url>:58081 \
  -e MESH_STATUS_INTERVAL=10 \
  tkr41850/mesh-node
```

**Node agent with extra targets:**

```bash
docker run -d --pull=always --restart unless-stopped \
  --name mesh-node1 \
  -p 58081:58081 \
  -e LEADER_URL=http://<leader-url>:58080 \
  -e NODE_URL=http://<node-url>:58081 \
  -e MESH_STATUS_INTERVAL=10 \
  -e NODE_EXTRA_TARGETS="10.0.0.99 10.0.0.100" \
  tkr41850/mesh-node
```

The node will ping and HTTP-check the extra targets each cycle alongside its normal peers. Results appear in the dashboard as non-collapsible cards with an "extra target" annotation and are excluded from pair status computation.

Data is persisted in `./data/` on the host. Check leader health at `http://localhost:58080/livez` and open the dashboard at `http://localhost:58581`.

### Port Management

Each container listens on the port specified in its URL. Docker maps the container port to a matching host port:

| Container | Container Port | Host Port |
|-----------|---------------|-----------|
| Leader API | from `LEADER_URL` (default `58080`) | `58080` |
| Leader Dashboard | `58581` | `58581` |
| Node HTTP | from `NODE_URL` (default `58081`) | `58081` |

When running **natively** without Docker, pass the URLs directly:

```bash
# Leader
go run ./cmd/leader

# Node
NODE_EXTRA_TARGETS="10.0.0.99 10.0.0.100" go run ./cmd/node
```

## Single-Architecture Builds

Build for the current platform:

```bash
# Leader
docker build --pull -f Dockerfile.leader.gobuild -t mesh-leader .

# Node
docker build --pull -f Dockerfile.node.gobuild -t mesh-node .
```

## Multi-Architecture Builds

Build for both `linux/amd64` and `linux/arm64`:

```bash
# Ensure buildx is available
docker buildx create --use 2>/dev/null || true

# Leader
docker buildx build --pull --platform linux/amd64,linux/arm64 \
  -t mesh-leader -f Dockerfile.leader.gobuild --load .

# Node
docker buildx build --pull --platform linux/amd64,linux/arm64 \
  -t mesh-node -f Dockerfile.node.gobuild --load .
```

Note: `--load` saves only the current architecture locally. Use `--push` to push a multi-arch manifest to a registry.

## CI/CD Setup

### Prerequisites

1. Create Docker Hub repositories: `<org>/mesh-leader` and `<org>/mesh-node`
2. Generate a [Docker Hub Personal Access Token](https://hub.docker.com/settings/security) (Read & Write)

### GitHub Secrets

Add these secrets to your GitHub repository (Settings → Secrets and variables → Actions):

| Secret | Value |
|--------|-------|
| `DOCKER_USERNAME` | Docker Hub username |
| `DOCKER_PASSWORD` | Docker Hub Personal Access Token |

### GitHub Variables (optional)

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCKER_ORG` | `github.repository_owner` | Docker Hub org for image tags |

### Workflow

The `.github/workflows/docker-publish.yml` workflow:

- **Trigger**: Push to `main`, tags (`v*`), or PR to `main`
- **Matrix**: Builds both `mesh-leader` and `mesh-node` in parallel
- **Platforms**: `linux/amd64` and `linux/arm64`
- **Push**: To Docker Hub on push/merge (not on PRs)
- **Tags**: `latest` (on main), semver (`v1.2.3`, `v1.2`), branch name
- **Cache**: GitHub Actions cache for layer reuse

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LEADER_URL` | `http://0.0.0.0:58080` | Leader URL (bind port extracted for Hypercorn; nodes/dashboard connect here) |
| `LEADER_HOST` | `0.0.0.0` | Leader bind address |
| `NODE_URL` | (auto-detect) | Node URL — hostname is registry identity, port is aiohttp listen port |
| `DATA_DIR` | `/app/data` | Data persistence directory |
| `MESH_STATUS_INTERVAL` | `10` | Check interval in seconds |
| `NODE_EXTRA_TARGETS` | (empty) | Space-separated additional target IPs to check each cycle (e.g. `"10.0.0.99 10.0.0.100"`); results are marked `is_extra` and excluded from pair status computation |

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
uv run python node.py --leader-url http://<leader>:58080 --node-url http://<this-node>:58080

# Dashboard
LEADER_URL=http://<leader>:58080 streamlit run mesh_status/dashboard.py --server.port 58581
```

Open `http://localhost:58581` (or the host IP) in a browser.

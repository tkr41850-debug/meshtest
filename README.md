# mesh-status

[![Build & Push Docker Images](https://github.com/{{REPO_OWNER}}/mesh-status/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/{{REPO_OWNER}}/mesh-status/actions/workflows/docker-publish.yml)

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

## Docker Images

Pre-built multi-arch images are available on Docker Hub:

| Image | Description |
|-------|-------------|
| `<org>/mesh-leader` | Leader + Dashboard |
| `<org>/mesh-node` | Node agent |

Replace `<org>` with the Docker Hub org or username used during build.

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

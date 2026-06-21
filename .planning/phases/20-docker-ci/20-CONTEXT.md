# Phase 20 Smart Discuss Context

## Phase Context
**Goal:** Install and start scripts are validated automatically in CI via Docker-based integration tests  
**Depends on:** Phase 18, Phase 19  
**Requirements:** TEST-01, TEST-02, TEST-03  

## Grey Areas & Decisions

### What base image for the test container?
- **Decision:** Ubuntu 24.04 LTS
- **Rationale:** Matches typical bare-metal deployments; has apt-get for git+curl; uv ships its own Python via install.sh
- **Rejected:** python:3.12-slim (doesn't test non-Docker install path), alpine (no bash by default)

### How does the CI workflow work?
- **Platform:** GitHub Actions on ubuntu-latest
- **Container used per step:** Build Dockerfile.ci-test → `docker run` for each test case
- **No Docker-in-Docker:** Standard `docker` CLI on the runner (Docker is available on ubuntu-latest)

### How to test start.sh --leader health?
- **Approach:** `docker run -d` to daemonize the container, wait for startup, then `docker exec` into it to run `curl -f http://localhost:58080/livez`
- **Alternative rejected:** Port mapping (requires coordinating free ports, adds complexity)

### Existing artifacts?
- Dockerfile.leader (+ entrypoint.sh with HEALTHCHECK) — already exists from v0.2
- Dockerfile.node — already exists from v0.2
- No .github/workflows/ exists — need to create

### What makes a "fresh container"?
- Container starts from Ubuntu 24.04 base WITHOUT mesh-status pre-installed
- Each test run starts from scratch (no cached install state)
- Created by `docker build -t mesh-test -f Dockerfile.ci-test .` fresh each CI run

## Deferred Ideas
- Docker Compose multi-node testing — not needed for v0.8 CI gate
- Pre-built Docker images in CI — v0.2 already had multi-arch build workflow (deleted); not in scope
- Integration test with real node agent — requires two containers; add in future milestone

## Open Questions
- (none — all decisions covered)

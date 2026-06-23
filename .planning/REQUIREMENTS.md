# Requirements: mesh-status

**Defined:** 2026-06-22
**Core Value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## v0.11 Requirements

Rewrite both mesh-leader and mesh-node in Go for minimal container image size and memory footprint. Produce Docker images, deploy via Docker Compose, and validate against the spec/ integration tests.

### Go Leader

- [x] **GO-LEAD-API**: Go leader implements POST /register, POST /submit, GET /data (90m/90h/90d), GET /node-list, GET /livez, GET /readyz, GET /healthz, POST /updateConfig — matching Python endpoint behavior
- [x] **GO-LEAD-PERSIST**: Go leader persists results to date-partitioned JSON Lines files (same format as Python implementation)
- [x] **GO-LEAD-PEER-PUSH**: Go leader pushes peer list and config updates to all registered nodes after registration/config changes
- [x] **GO-LEAD-REGISTRY**: Go leader maintains thread-safe in-memory node registry with mutex-equivalent synchronization

### Go Node

- [x] **GO-NODE-PING**: Go node runs ICMP ping via os/exec against all peers with configurable timeout
- [x] **GO-NODE-HTTP-CHECK**: Go node runs HTTP GET /healthz against all peers concurrently with configurable timeout
- [x] **GO-NODE-SUBMIT**: Go node submits check results to leader after each cycle, buffers on failure and retries
- [x] **GO-NODE-PEER-LISTENER**: Go node runs HTTP server to receive peer push and config updates from leader
- [x] **GO-NODE-CYCLE**: Go node orchestrates full check cycle: fetch peers → run checks → submit results, on configurable interval

### Docker

- [x] **GO-DOCKER-LEADER**: Dockerfile for Go leader producing minimal (<10MB) image
- [x] **GO-DOCKER-NODE**: Dockerfile for Go node producing minimal (<10MB) image
- [x] **GO-DOCKER-COMPOSE**: docker-compose.yml running Go leader + Go node + existing frontend

### Testing

- [x] **GO-SPEC-TESTS**: spec/ integration tests pass against Docker-hosted Go leader

### Preservation

- [x] **GO-KEEP-PYTHON**: Python source files remain in the repository (not deleted)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Frontend rewrite | Existing Vite+TS frontend works with any backend serving the same API |
| Feature enhancements | This milestone is about equivalence — match existing behavior exactly |
| Streamlit dashboard | Python-only feature; not ported to Go |
| Windows support | Python scripts serve Windows; Go leader/node can be cross-compiled later |
| CI pipeline changes | Existing Makefile/CI unchanged; Go build added separately |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| GO-LEAD-API | Phase 31 | ✅ Complete |
| GO-LEAD-REGISTRY | Phase 31 | ✅ Complete |
| GO-LEAD-PERSIST | Phase 32 | ✅ Complete |
| GO-LEAD-PEER-PUSH | Phase 32 | ✅ Complete |
| GO-NODE-PING | Phase 33 | ✅ Complete |
| GO-NODE-HTTP-CHECK | Phase 33 | ✅ Complete |
| GO-NODE-SUBMIT | Phase 33 | ✅ Complete |
| GO-NODE-CYCLE | Phase 33 | ✅ Complete |
| GO-NODE-PEER-LISTENER | Phase 34 | ✅ Complete |
| GO-DOCKER-LEADER | Phase 35 | ✅ Complete |
| GO-DOCKER-NODE | Phase 35 | ✅ Complete |
| GO-DOCKER-COMPOSE | Phase 35 | ✅ Complete |
| GO-SPEC-TESTS | Phase 35 | ✅ Complete |
| GO-KEEP-PYTHON | Phase 35 | ✅ Complete |

**Coverage:**
- v0.11 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0 ✓

---

*Requirements defined: 2026-06-22*
*Last updated: 2026-06-22 after initial definition*

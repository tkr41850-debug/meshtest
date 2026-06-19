# Requirements: mesh-status

**Defined:** 2026-06-18
**Core Value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## v3 Requirements

Requirements for v0.3 — Dashboard Fixes and UX improvements.

### Dashboard Bug Fixes

- [ ] **DASHF-01**: Fix `st.rerun(scope="fragment")` error so dashboard auto-refreshes without StreamlitAPIException

### Data Latency Grace Period

- [ ] **DASHD-01**: Status calculation allows up to 2-minute delay before marking node data as "Not Available" (data from different nodes does not arrive all at once)

### Dashboard UI Enhancements

- [ ] **DASHU-01**: Per-node-pair details dropdown shows uptime summary card (UptimeRobot-style) with status indicator, uptime percentage, latest latency, and last check time

## v3.5+ Requirements

Deferred to future release. Tracked but not in current roadmap.

(None yet)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Backend architecture changes | v0.3 is exclusively dashboard UI/fix layer — no leader/node agent changes unless needed for data latency |
| New monitoring metrics | No packet loss, traceroute, or bandwidth features in this milestone |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| DASHF-01 | — | Pending |
| DASHD-01 | — | Pending |
| DASHU-01 | — | Pending |

**Coverage:**
- v3 requirements: 3 total
- Mapped to phases: 0
- Unmapped: 3 ⚠️

---
*Requirements defined: 2026-06-18*
*Last updated: 2026-06-18 after initial definition*

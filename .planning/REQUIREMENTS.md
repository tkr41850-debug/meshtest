# Requirements: mesh-status

**Defined:** 2026-06-19
**Core Value:** A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## v0.7 Requirements

### Bug Fixes

- [ ] **FIX-01**: CheckResult interface uses `ping_ok: boolean` / `http_ok: boolean` matching real API response
- [ ] **FIX-02**: `aggregateByMinute` checks `ping_ok`/`http_ok` fields (not `ping_status`/`http_status`)
- [ ] **FIX-03**: Backend 30d endpoint infers `node_ip` from `_results` when disk records have empty `node_ip`

### Dashboard

- [ ] **DASH-13**: 30-day view always expanded — no `<details>` expanders, sticky source headers
- [ ] **DASH-14**: Visible gap between matrix table and cards in 30-minute tab
- [ ] **DASH-15**: Two separate history bar rows per pair (ICMP + HTTP) instead of single gradient bar
- [ ] **DASH-16**: Shared `bars.ts` with HSB-interpolated `renderBars(bars: {percent, tooltip}[])` — hue 0° (red) at 0% → 120° (green) at 100%

### Testing

- [ ] **TEST-04**: All Vitest fixtures updated for `ping_ok`/`http_ok`; tests cover dual-row bars, HSB colors, flat day30 layout

## v2 Requirements

None deferred.

## Out of Scope

| Feature | Reason |
|---------|--------|
| New features or capabilities | v0.7 is a bugfix and polish milestone only |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| FIX-01 | Phase 15 | Pending |
| FIX-02 | Phase 15 | Pending |
| FIX-03 | Phase 16 | Pending |
| DASH-13 | Phase 16 | Pending |
| DASH-14 | Phase 16 | Pending |
| DASH-15 | Phase 16 | Pending |
| DASH-16 | Phase 15 | Pending |
| TEST-04 | Phase 15 | Pending |

**Coverage:**
- v0.7 requirements: 8 total
- Mapped to phases: 8
- Unmapped: 0 ✓

---
*Requirements defined: 2026-06-19*
*Last updated: 2026-06-19 after initial definition*

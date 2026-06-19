# Roadmap: mesh-status

## Overview

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN.

## Milestones

### v0.1 — mesh-status initial release (Complete ✅)

All 5 phases delivered: Leader Core & Registration, Node Agent, Persistence & Data API, Integration Tests, Streamlit Dashboard + cross-phase integration fixes.

See archived roadmap: `.planning/milestones/v0.1-ROADMAP.md`
See archived requirements: `.planning/milestones/v0.1-REQUIREMENTS.md`

### v0.2 — Containerize mesh-status (Complete ✅)

Dockerized leader+dashboard and node components with CI/CD pipeline and multi-arch support.

See archived roadmap: `.planning/milestones/v0.2-ROADMAP.md`
See archived requirements: `.planning/milestones/v0.2-REQUIREMENTS.md`

### v0.3 — Dashboard Fixes (Complete ✓)

Fixed dashboard bugs, added data latency grace period, and enhanced per-node-pair detail views with UptimeRobot-style cards.

### v0.4 — Dashboard UI Polish (In Progress)

Tuned refresh rate, added inline per-check-type uptime display, fixed matrix labels, and resolved HTML rendering in expander cards.

## Phase Structure

### Phase 5: Backend — Data Latency Grace Period (Complete ✓)

**Goal:** Prevent premature "NotAvailable" status when node data arrives with up to 2-minute skew

**Requirements:** DASHD-01

**Success criteria:**
- [x] Status calculation accepts data arriving up to 120s after the expected interval without marking "NotAvailable"
- [x] Existing OK/Pending/NotAvailable status values are preserved for genuinely stale data
- [x] All existing tests pass (no regression in status logic)

### Phase 6: Frontend — Dashboard Bug Fix + UptimeRobot-style Details (Complete ✓)

**Goal:** Fix auto-refresh crash and replace row-based expander details with rich summary cards

**Requirements:** DASHF-01, DASHU-01

**Success criteria:**
- [x] Dashboard auto-refreshes without `StreamlitAPIException`
- [x] Each node-pair expander shows an UptimeRobot-style summary card with: status badge, uptime %, latest ping/HTTP latency, last check timestamp
- [x] Cards are visually distinct from the current flat table layout
- [x] All existing dashboard views (30m matrix, 30d view) remain functional

### Phase 7a: Display & Refresh Tuning

**Goal:** Improve dashboard responsiveness and info density

**Requirements:** v0.4 items 2-4

**Success criteria:**
- [x] Auto-refresh interval reduced from 30s to 10s with cache TTL adjusted to 8s
- [x] Refresh indicator text updated to reflect new interval
- [x] Card shows per-check-type uptime inline with latencies (Ping: Xms (Y%), HTTP: Xms (Y%))
- [x] Matrix column headers show short numeric labels (e.g., "1" instead of "ai") with full hostname on hover
- [x] All existing tests continue to pass

### Phase 7b: HTML Rendering Fix

**Goal:** Fix raw HTML code display in expander cards

**Requirements:** v0.4 item 1

**Success criteria:**
- [x] Uptime info renders as styled text, not raw HTML code
- [x] No `</div>` or other HTML tags visible in rendered output
- [x] Card visual appearance preserved
- [x] All existing tests pass

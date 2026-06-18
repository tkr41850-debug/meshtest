# mesh-status

## What This Is

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN. A leader server orchestrates node registration and collects periodic connectivity check results (ICMP ping + HTTP /healthz) between all node pairs. A Streamlit dashboard visualizes mesh connectivity over rolling 30-minute or 30-day windows.

## Core Value

A node must be able to detect and report whether it can reach every other node in the mesh, and the leader must present an accurate, up-to-date connectivity view.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Leader starts on port 58080, accepts node registrations with node IP
- [ ] Leader distributes full node IP list to all registered nodes on each registration
- [ ] Node runs periodic checks every N seconds (N configurable on leader, default 10s) against all other nodes: ICMP ping (via system ping) and HTTP GET /healthz
- [ ] Node submits check results to leader after each check cycle
- [ ] On submission failure, node buffers results in memory and retries next cycle
- [ ] Leader persists check results to JSON files: data/[yyyy]/[mm]/[dd].json, writes aggregated data every hour
- [ ] Leader exposes data API endpoint for frontend queries
- [ ] Leader serves Streamlit frontend showing mesh connectivity
- [ ] Frontend supports two time windows: 30 minutes (last 30 checks) and 30 days (daily aggregated uptime)
- [ ] Node status values: OK, Pending (no result yet, no future data expected), NotAvailable (no result but future data expected)
- [ ] Registration script (register.py) accepts node-ip and leader-ip via argv or stdin

### Out of Scope

- Authentication / access control — VPN is trusted network for prototype
- Database backend — JSON file storage sufficient for prototype scale
- Real-time push/WebSocket — Frontend polls the data endpoint
- Encryption of data in transit or at rest — prototype

## Context

- Python prototype, Quart for HTTP server, Streamlit for dashboard
- Deployed across multiple VMs on different geographies connected via VPN WAN
- Data is small per check, retained in memory on nodes between submissions
- Leader writes JSON files hourly to avoid memory/disk pressure
- System `ping` binary used for ICMP (shelled out)

## Constraints

- **Port**: Leader must listen on 58080
- **Language**: Python (fast prototyping)
- **Framework**: Quart (async HTTP server), Streamlit (frontend)
- **Deployment**: Multi-VM over VPN WAN

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Quart instead of FastAPI | Simpler async server, fewer dependencies for prototype | — Pending |
| JSON file persistence | Quick to implement, inspectable, no DB setup | — Pending |
| System ping binary | Avoids root/capabilities for raw ICMP sockets | — Pending |
| No auth | VPN is trusted, prototype speed | — Pending |
| Port 58080 | Avoids privileged ports, unlikely to conflict | — Pending |

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-06-17 after initialization*

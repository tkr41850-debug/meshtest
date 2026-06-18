# Feature Research: Distributed Mesh Connectivity Testing

**Domain:** Distributed network connectivity monitoring (mesh ping / health check)
**Researched:** 2026-06-18
**Confidence:** HIGH

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist in any mesh connectivity monitoring tool. Missing these = product feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Node registration works | Core mechanism for mesh membership — no nodes = no mesh | LOW | Registration script (register.py) must accept node-ip and leader-ip; must propagate updated peer list back to all nodes |
| Accurate ICMP ping checks | Primary connectivity signal. Tools like Goldpinger, Smokeping, Blackbox Exporter all provide this as baseline | MEDIUM | Shell out to system `ping` binary; measure RTT, detect packet loss. Need to handle cross-VPN ICMP (some providers block ICMP) |
| Accurate HTTP /healthz checks | Service-level health signal. Standard pattern (K8s, Nomad, etc.) | LOW | Simple GET request with timeout; verify 2xx status code |
| Check results reach leader | Without results reaching the leader, the dashboard is empty. Network flakiness makes this non-trivial | LOW | Node buffers results in memory on submission failure and retries next cycle |
| Dashboard shows real data | If the Streamlit dashboard is blank or shows stale data, tool is unusable | MEDIUM | Two time windows must show actual check results with correct timestamps |
| Node status is clearly indicated | Operators need to know "is this node reachable or not?" | LOW | Three states: OK, Pending (no future data expected), NotAvailable (expected but missing). Mirror patterns from Prometheus `probe_success` |
| Check interval is configurable | Operators need to balance check frequency vs network load. Goldpinger, Meshping, Smokeping all support configurable intervals | LOW | Default 10s, configurable via leader. Must be per-mesh, not per-node |
| Results survive leader restart | If the leader process restarts, all historical data is lost without persistence | MEDIUM | JSON files written to disk every hour. On startup, leader reads existing data files to serve historical queries |
| Peer list is automatically distributed | Adding a node to the mesh must cause all other nodes to discover it. Without this, the mesh is static and manual | MEDIUM | On each registration, leader pushes updated node IP list to all registered nodes. Matches pattern from SignalScope SSMP mesh fabric |
| Basic working visualization | The dashboard must at minimum show which nodes can reach which, with latency information | MEDIUM | Streamlit dashboard with some form of connectivity matrix or per-node time series |

### Differentiators (Competitive Advantage)

Features that set mesh-status apart from existing tools. Not required for basic function, but create meaningful differentiation.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Mesh push model (node-initiated checks submit to leader) | Unlike Prometheus pull model which requires reverse connectivity, nodes push results. Critical for VPN WAN topologies where leader can't reach nodes | MEDIUM | This is the architectural core differentiator. Leader is passive recipient; nodes are active senders. Mirror approach from DNMS (distributed ping + traceroute, aggregated centrally). |
| No database dependency | Zero operational overhead. No PostgreSQL, no Prometheus, no SQLite. A single `data/` directory is the entire durable state | LOW | Matches the prototype constraint. Trade-off: no query language, no retention policies, no replication. But for the target scale (tens of nodes, not thousands), this is a net positive |
| Hourly JSON rotation with YYYY/MM/DD file structure | Data is human-readable, debuggable, and trivially examinable with `cat`, `jq`, or `less`. No specialized tooling needed | LOW | Structure: `data/2026/06/18.json`. Hourly aggregation reduces disk writes. Enables easy manual inspection and ad-hoc analysis |
| Dual time window design (30min + 30day) | Purpose-built views rather than a generic Grafana. 30min = last N checks (micro view for current status). 30day = daily aggregated uptime (macro view for trends) | MEDIUM | The 30min view shows raw check granularity. The 30day view shows aggregated daily uptime percentages. Smokeping similar but more complex — this is simpler and more focused |
| Buffer-and-retry on submission failure | Nodes are expected to experience intermittent connectivity. Buffering in memory and retrying prevents data loss without requiring durable storage on the node | LOW | Simple pattern: on POST failure, append to in-memory buffer; on next check cycle, attempt to flush buffer first. Goldpinger and DNMS have similar but more complex retry logic |
| Streamlit dashboard (Python-native, instant deploy) | A Grafana setup requires separate infrastructure. Streamlit is `pip install streamlit && streamlit run dashboard.py`. For Python-heavy teams, this is dramatically simpler | MEDIUM | Streamlit's simplicity is a feature, not a limitation. For the target use case (small mesh, operator is the developer), a full observability platform is overkill. This is a deliberate anti-Grafana choice |
| Registration via simple Python script | `python register.py --node-ip 10.0.0.1 --leader-ip 10.0.0.2` or pipe via stdin. No DNS, no service discovery, no config management needed | LOW | Script-based registration is aligned with the "no infrastructure" philosophy. Accepts stdin for automation without requiring a config file format |
| Meshing without Kubernetes | Unlike Goldpinger (tightly coupled to K8s DaemonSet) or MeshMonitor (Meshtastic-specific), this tool works on any Linux VMs on any VPN | HIGH | The entire design is K8s-independent. No pods, no services, no cluster DNS. This is a genuine differentiator for non-K8s infrastructure |
| Status triage: Pending vs NotAvailable | Distinguishes "we don't know yet" (Pending) from "we expect data but didn't get it" (NotAvailable). Critical for correctly interpreting an empty dashboard on first deploy | LOW | A subtle but important UX choice. Newly registered nodes show Pending (not FAIL) until their first check cycle completes. NotAvailable = node was previously healthy but missed checks |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for this project's scope and philosophy.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| Authentication / access control | "What if someone hits the API endpoint?" | VPN is trusted; auth adds complexity for zero threat-model benefit. Adds session management, token rotation, login page to Streamlit | Keep behind VPN. If auth becomes needed, add simple API key header check, not full OAuth |
| Database backend (PostgreSQL, SQLite) | "JSON files don't scale" | For prototype scale (<50 nodes, <100 checks/min), JSON is fine. DB adds deployment dependency, migration management, connection pooling | JSON files for prototype. If scale demands change, migrate to SQLite (zero-server, file-based) as natural step |
| Real-time WebSocket updates | "Dashboard should update instantly" | WebSockets add connection management, reconnection logic, server-side state. Polling every N seconds is simpler, more robust, and adequate for 10-30s check intervals | Streamlit's built-in polling (`st.rerun` or `@streamlit.fragment` with `run_every=N`) achieves near-real-time without protocol complexity |
| Encryption in transit or at rest | "Data should be encrypted" | VPN already provides transit encryption. At-rest encryption adds key management, performance cost, and debugging complexity | Rely on VPN for transit. For at-rest, filesystem-level encryption (LUKS, eCryptfs) if needed |
| Historical data beyond 30 days | "I want to see last year's data" | 30-day retention is explicit. Longer retention needs rotation policy, archival strategy, storage management | Keep 30-day rolling window per scope. If users need more, archive `data/` directories manually or add an archive script — but don't build it into the dashboard |
| Prometheus / Grafana integration | "Use the standard stack" | Prometheus pull model doesn't fit push-based mesh. Adding Prometheus means managing a TSDB, scrape configs, recording rules, alertmanager. Grafana adds another deployment | Keep Streamlit as the sole frontend. If Prometheus integration is needed later, expose a `/metrics` endpoint alongside the JSON API |
| Containerization / Docker Compose | "It's the modern way to deploy" | For prototype, the overhead of Docker knowledge, Dockerfiles, compose files, image builds, registries slows iteration. Python script + systemd is simpler | Ship as Python package (`pip install`). If Docker becomes needed for deploy reproducibility, add it after prototype validation |
| Alerting / notifications | "I want to know when a node goes down" | Alerting is a product in itself: deduplication, escalation, silence, notification channels. Adding it prematurely creates maintenance burden and false-positive fatigue | The dashboard is the alerting mechanism for prototype. If alerting is needed, add simple email or webhook on the leader side, not a full alert management system |
| Multi-protocol probes (DNS, TCP, gRPC, etc.) | "Blackbox Exporter does HTTP, DNS, TCP, ICMP..." | Each additional protocol adds probe configuration, timeout management, result schema changes, dashboard complexity | Stick to ICMP ping + HTTP /healthz for prototype. These cover 90% of connectivity issues. Add protocols only after validating the core |
| SNMP / NetFlow / traffic analysis | "Real network monitoring includes traffic" | SNMP polling, flow collection, MIB browsing are entirely different domains. Mixing them dilutes the focused connectivity-testing purpose | This is a connectivity tester, not a network monitoring platform. SNMP and flow analysis go in a different product |
| Distributed tracing / path analysis / MTR | "I want to know where the failure is" | MTR/traceroute adds complexity: root permissions for raw sockets, path storage, visualization. This is a "detect" tool, not a "diagnose" tool | MTR integration is a natural v2 feature, but should be explicitly deferred. The 30min/30day views tell *that* connectivity failed, not *where* |

## Feature Dependencies

```
Node Registration
    └──requires──> Python HTTP server (Quart listening on port 58080)
                       └──requires──> Leader node IP is known and reachable

Distribute Peer List
    └──requires──> Node Registration (leader needs registered nodes)
    └──requires──> Registered nodes have working HTTP client

Run Periodic Checks
    └──requires──> Peer list distributed (node needs targets to check)
    └──requires──> System `ping` binary installed on node
    └──requires──> Target nodes have /healthz endpoint

Submit Results to Leader
    └──requires──> Run Periodic Checks (results need data)
    └──requires──> Leader API endpoint reachable from node

Buffer-and-Retry
    └──requires──> Submit Results to Leader (retry is about submission failure)
                         └──enhances──> Reliability of data collection

Persist to JSON (hourly)
    └──requires──> Submit Results to Leader (leader needs results to persist)
    └──requires──> Leader file system writable

Data API Endpoint
    └──requires──> Persist to JSON (API reads persisted data)
    └──requires──> Node Registration (API needs to know which nodes exist)

Streamlit Dashboard (30min)
    └──requires──> Data API Endpoint (dashboard reads from API)
    └──requires──> Run Periodic Checks (dashboard shows check results)

Streamlit Dashboard (30day)
    └──requires──> Persist to JSON (30day view needs aggregated historical data)
    └──requires──> Dashboard (30min) (shares dashboard infrastructure, time-window filter is additive)

Node Status (OK/Pending/NotAvailable)
    └──requires──> Node Registration (Pending is set on registration before first check)
    └──requires──> Run Periodic Checks (OK is set when check succeeds)
    └──requires──> Detection of missed checks (NotAvailable is set when expected check doesn't arrive)
```

### Dependency Notes

- **Peer List Distribution is the critical path bottleneck.** Until a node has the peer list, it cannot check anything. This must be built and tested first.
- **Buffer-and-Retry enhances reliability but does not block the dashboard.** If retry logic is absent, the dashboard will show gaps during network blips — functional but with data loss.
- **30-day view depends on persistence, 30-minute view does not.** The 30-minute view can work entirely from the latest hour's data. The 30-day view requires aggregated daily files.
- **Node status logic depends on time-aware evaluation.** NotAvailable requires knowing a check *should* have happened. This means the leader must track when each node last submitted results and compare against expected intervals.

## MVP Definition

### Launch With (v1)

Minimum viable product — what's needed to validate the concept.

- [x] Leader starts on port 58080, accepts node registrations with node IP — *essential: mesh cannot form without it*
- [x] Leader distributes full node IP list to all registered nodes on each registration — *essential: nodes need targets*
- [x] Node runs periodic checks (ICMP ping + HTTP /healthz) against all peers — *core functionality*
- [x] Node submits check results to leader after each check cycle — *without this, leader has no data*
- [x] On submission failure, node buffers results in memory and retries — *critical for lossy VPN WAN*
- [x] Leader persists check results to JSON files: data/[yyyy]/[mm]/[dd].json, writes hourly — *without this, data is lost on restart*
- [x] Leader exposes data API endpoint for frontend queries — *dashboard needs data source*
- [x] Leader serves Streamlit frontend showing mesh connectivity — *primary user interface*
- [x] Frontend supports 30-minute time window (last ~30 checks) — *immediate operational view*
- [x] Node status values: OK, Pending, NotAvailable — *clear signal of mesh health*
- [x] Registration script (register.py) accepts node-ip and leader-ip via argv or stdin — *automated on-boarding*

### Add After Validation (v1.x)

Features to add once core is working and prototype validated.

- [ ] 30-day aggregated uptime dashboard view — *trigger: users need trend/historical view; depends on enough data accumulated*
- [ ] Peer-to-peer latency matrix view in dashboard — *trigger: users need to compare latency between all pairs at a glance*
- [ ] Configurable check interval (leader-controlled) — *trigger: default 10s is too fast or too slow for actual deployment*
- [ ] Node de-registration / cleanup — *trigger: nodes leave the mesh and stale entries accumulate*
- [ ] Check timeout configuration (per-protocol or global) — *trigger: default timeout causes false negatives on slow links*

### Future Consideration (v2+)

Features to defer until product-market fit is established.

- [ ] MTR / traceroute integration for path diagnostics — *trigger: users report connectivity failures and need to know where*
- [ ] Alert webhooks (Slack, email) — *trigger: users are watching the dashboard 24/7 and want notifications instead*
- [ ] Docker deployment with docker-compose — *trigger: manual Python setup becomes a pain point*
- [ ] /metrics endpoint for Prometheus scraping — *trigger: users want to integrate with existing Prometheus/Grafana infrastructure*
- [ ] Multi-leader / high-availability for leader — *trigger: leader becomes single point of failure that matters*
- [ ] API key-based lightweight auth — *trigger: dashboard is exposed beyond trusted VPN*

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Node registration | HIGH | LOW | P1 |
| Peer list distribution | HIGH | MEDIUM | P1 |
| ICMP ping checks | HIGH | MEDIUM | P1 |
| HTTP /healthz checks | HIGH | LOW | P1 |
| Submit results to leader | HIGH | LOW | P1 |
| Buffer-and-retry | MEDIUM | LOW | P1 |
| Dashboard (30min view) | HIGH | MEDIUM | P1 |
| JSON file persistence | HIGH | MEDIUM | P1 |
| Data API endpoint | HIGH | LOW | P1 |
| Node status (OK/Pending/NotAvailable) | MEDIUM | LOW | P1 |
| Registration script | HIGH | LOW | P1 |
| Dashboard (30day view) | MEDIUM | MEDIUM | P2 |
| Configurable check interval | MEDIUM | LOW | P2 |
| Node de-registration | MEDIUM | LOW | P2 |
| Latency matrix visualization | MEDIUM | MEDIUM | P2 |
| MTR/traceroute integration | MEDIUM | HIGH | P3 |
| Alert webhooks | MEDIUM | MEDIUM | P3 |
| Docker deployment | LOW | MEDIUM | P3 |
| Prometheus /metrics endpoint | LOW | LOW | P3 |
| Multi-leader HA | LOW | HIGH | P3 |
| API key auth | LOW | LOW | P3 |

**Priority key:**
- P1: Must have for launch (11 features)
- P2: Should have, add when possible (4 features)
- P3: Nice to have, future consideration (6 features)

## Competitor Feature Analysis

| Feature | Goldpinger (Bloomberg) | SignalScope | DNMS | Meshping | Smokeping | Prometheus BBE | **mesh-status (our approach)** |
|---------|----------------------|-------------|------|----------|-----------|----------------|-------------------------------|
| Node registration | Pod auto-discovery via K8s API | Agent registration with SSMP | Memberlist-based peer discovery | Config file or env vars | Config file | Prometheus scrape config | Python script → leader API |
| Check mechanism | HTTP ping between pods (K8s) | ICMP, HTTP, DNS, TCP, gRPC, + | Ping + traceroute across all peers | ICMP ping + traceroute | ICMP ping with histogram buckets | ICMP, HTTP, DNS, TCP, gRPC | ICMP ping + HTTP /healthz |
| Check origin | Pull (Prometheus scrapes agents) | Push (agent submits to central) | Push (agent to aggregator) | Push (p2p, each instance exposes) | Push (local daemon writes RRD) | Pull (Prometheus scrapes exporter) | Push (node submits to leader) |
| Data storage | Prometheus TSDB | InfluxDB or Prometheus | In-memory + API | SQLite | RRD files | Prometheus TSDB | JSON files (YYYY/MM/DD) |
| Frontend | Built-in lightweight graph | WebSocket live dashboard | REST API + optional dashboard | Built-in SVG map + graphs | CG-based "smoke" graphs | Grafana (external) | Streamlit (embedded) |
| K8s dependency | Yes (DaemonSet) | No | No | No | No | No | No |
| Protocol depth | HTTP + optional UDP | 10+ protocols | ICMP + traceroute | ICMP + traceroute | ICMP | ICMP + HTTP + DNS + TCP + gRPC | ICMP + HTTP (focused) |
| Database required | Prometheus | Yes (Influx/Prom) | No | SQLite | No (RRD) | Prometheus | No |
| Real-time UI | Polling | WebSocket streaming | SSE | Polling | Static image gen | Via Grafana | Polling (Streamlit rerun) |
| Auth model | K8s RBAC | API tokens | None | None | None | TLS + basic auth | None (VPN trusted) |
| Alerting | Prometheus Alertmanager | Built-in threshold alerts | None | None | Built-in | Via Alertmanager | Deferred (v2) |
| Mesh focus | Full mesh (all pods to all pods) | Full mesh (SSMP) | Full mesh (every node pings every node) | Mesh peering (share targets) | Star (center to targets) | Star (exporter to targets) | Full mesh (all nodes check all nodes) |

## Sources

- **Goldpinger** (Bloomberg): https://github.com/bloomberg/goldpinger — K8s mesh connectivity testing (HIGH confidence, active project)
- **SignalScope**: https://signalscope.io/ — Full mesh SSMP agent, multi-protocol (MEDIUM confidence, commercial site)
- **DNMS**: https://pkg.go.dev/github.com/jacksontj/dnms — Distributed ping + traceroute with per-link fault attribution (HIGH confidence, Go docs)
- **Meshping**: https://github.com/Svedrin/meshping — Distributed ping with traceroute and topology maps (HIGH confidence, stable project)
- **Smokeping**: https://oss.oetiker.ch/smokeping/ — Classic latency monitoring (HIGH confidence, established tool)
- **Prometheus Blackbox Exporter**: https://github.com/prometheus/blackbox_exporter (HIGH confidence, v0.28.0, 2025-12)
- **Smokeping_prober**: Prometheus community project for histogram-based ping (MEDIUM confidence, referenced in Prometheus developer discussions)
- **Mehsh**: https://github.com/easybill/mehsh — UDP ping mesh (HIGH confidence, stable project)
- **PingPlotter**: https://www.pingplotter.com/ — Commercial distributed monitoring (MEDIUM confidence, commercial tool)
- **Uptime Kuma**: 60k+ stars, simple uptime monitoring (HIGH confidence)
- **Gatus**: 6k+ stars, health dashboard (HIGH confidence)
- **PRTG** (Paessler): Enterprise distributed monitoring with remote probes (HIGH confidence, established commercial tool)
- **network_exporter**: https://github.com/syepes/network_exporter — ICMP/MTR/TCP/HTTP Prometheus exporter (HIGH confidence, active)
- **ACM SIGCOMM '15 Pingmesh paper**: https://conferences.sigcomm.org/sigcomm/2015/pdf/papers/p139.pdf — Microsoft's data center latency measurement system (HIGH confidence, peer-reviewed)
- **"Best Open Source Monitoring Tools in 2026"** comparison: https://dev.to/devhelm/best-open-source-monitoring-tools-in-2026-7-self-hosted-options-compared-4l8h (MEDIUM confidence, blog comparison)

---
*Feature research for: Distributed mesh connectivity testing tool (mesh-status)*
*Researched: 2026-06-18*

# Phase 36: mesh-node NODE_EXTRA_TARGETS — extra node targets for additional diagnostics, leader handles out-of-network gracefully, frontend displays as extra rows

**Gathered:** 2026-06-24
**Status:** Ready for planning

<domain>
## Phase Boundary

Add NODE_EXTRA_TARGETS support to mesh-node: node reads space-separated extra targets from env var, includes them in every check cycle alongside regular peers, marks results as "extra" so the leader stores them as node→extra (not extra→[any]), and the frontend displays them as extra rows below the main mesh cards per source node.

</domain>

<decisions>
## Implementation Decisions

### Data Model
- Extra vs mesh differentiation: Add `is_extra` boolean field to `CheckResult` (and `CheckResultWithNode`) — true for extra target checks
- Extra checks submitted via the existing `/submit` endpoint (same payload, just with `is_extra: true` on applicable checks)
- Leader stores extra checks in the same `ResultsStore.results` map (same `nodeIP → []CheckResult`), but the `is_extra` flag distinguishes them
- 90m/90h/90d queries include extra checks in the `checks` array but NOT in `statuses` computation (filtered out of `checkPairStatus`)
- No separate storage, no `/submit-extra` endpoint

### Leader Storage Semantics
- Extra target results stored as `source_node_ip → {target_ip, is_extra: true, ...}`
- NO reverse entry stored (no `extra_target_ip → source_node_ip`)
- Extra target results NOT included in `AllIPs()` or pair status computation
- Query layer filters out `is_extra` checks when computing `statuses`

### Node Configuration & Cycle
- `NODE_EXTRA_TARGETS` env var: space-separated hostnames/IPs (no config file, no leader push)
- No explicit DNS resolution — pass hostname directly to ping/HTTP, let OS resolve
- Extra targets checked every cycle (same interval as normal peers)
- Same failure handling as regular peers (logged, buffered)
- Extra target results submitted in the same payload with `is_extra: true`

### Frontend Display
- Under each source node's card group: main mesh peers first, then extra target results
- Extra target cards are non-collapsible (no "Extra Targets" section header)
- Each extra target card has a small note text (e.g., "extra target") rather than a dedicated header
- Extra target results fetched via the same `/data?window=90m` endpoint (checks array includes them)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `CheckResult` struct in `internal/leader/models.go:11-17` — needs `IsExtra bool` field
- `CheckResultWithNode` struct in `internal/leader/results.go:47-54` — needs `IsExtra bool` field
- `CheckCycleResult` type alias in `internal/node/node.go:33` — aliases `leader.CheckResult`, picks up field automatically
- `SubmitResults` in `internal/node/node.go:62-104` — same endpoint, same payload
- `RunCheckCycle` in `internal/node/node.go:119-172` — needs to also iterate over extra targets
- `checkPairStatus` in `internal/leader/results.go:101-117` — needs to skip `is_extra` checks
- Frontend `types.ts` — `CheckResult` type needs `is_extra` field
- Frontend `cards.ts` / `card.ts` — needs to render extra target rows

### Established Patterns
- TDD: write failing test first for every behavioral change
- Go standard library `net/http` (no third-party router)
- Frontend: TypeScript, Vite, DOM manipulation (no framework)

### Integration Points
- `cmd/node/main.go` — read `NODE_EXTRA_TARGETS` env var and pass to `NewNode` or call a setter
- `internal/node/node.go` — add `ExtraTargets []string` field to `Node` struct
- `internal/leader/models.go` — add `IsExtra bool` to `CheckResult`
- `internal/leader/results.go` — add `IsExtra bool` to `CheckResultWithNode`, filter in `checkPairStatus`
- Frontend `api.ts` / `types.ts` — pass through `is_extra`, add `extra_targets` to types
- Frontend `cards.ts` — render extra target rows below main cards
</code_context>

<specifics>
## Specific Ideas

- Extra target cards: non-collapsible, immediately below main mesh peer cards for the same source node
- Small annotation text on the card (e.g., "extra target") rather than an "Extra Targets" section header
- Use a subtle visual indicator (different background tint or icon) to distinguish extra target cards from mesh peer cards
- No separate tab or section — keep everything in the existing cards layout

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

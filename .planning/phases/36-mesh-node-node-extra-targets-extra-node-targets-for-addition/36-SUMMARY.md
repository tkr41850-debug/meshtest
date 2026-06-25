# Phase 36: NODE_EXTRA_TARGETS — Summary

## Goal
Add support for extra target IPs that the node checks every cycle alongside normal peers, marked with `is_extra` flag, excluded from pair status computation, and displayed as non-collapsible cards with "extra target" annotation in the frontend.

## What Was Done

### Data Model
- `IsExtra bool` field added to `CheckResult` (`internal/leader/models.go:17`)
- `IsExtra bool` field added to `CheckResultWithNode` (`internal/leader/results.go:54`)
- `checkPairStatus` skips results with `IsExtra=true` (`internal/leader/results.go:109`)
- `flushOnce` and `Query90m` propagate `IsExtra` through persistence/read pipelines

### Node
- `ExtraTargets []string` field on `Node` struct, `SetExtraTargets()` method
- `RunCheckCycle` checks extra targets with `IsExtra: true`, HTTP on port 80
- `cmd/node/main.go` reads `NODE_EXTRA_TARGETS` env var (space-separated)

### Frontend
- `is_extra?: boolean` on `CheckResult` TypeScript interface
- `cardHtml` accepts `isExtra` param, shows "extra target" annotation
- `renderCards` separates normal/extra checks, renders extra cards below main cards per source

## Tests Added
- **Go**: `TestExtraTargetExcludedFromStatuses` (leader), `TestSetExtraTargets`, `TestRunCheckCycleWithExtraTargetsOnly`, `TestRunCheckCycleWithPeersAndExtraTargets` (node)
- **Frontend**: 4 tests — extra card rendering, source-group placement, no annotation on normal cards, summary label excludes extra targets

## Test Results
- 56 Go tests pass
- 57 frontend tests pass
- `make ci` — all 84 Python + 57 frontend + Go tests + build pass

## Files Changed
```
 .planning/ROADMAP.md           |  13 ++++
 .planning/STATE.md             |   5 +-
 cmd/node/main.go               |   7 ++
 frontend/src/mesh.test.ts      | 155 +++++++++++++++++++++++++++++++
 frontend/src/types.ts          |   1 +
 frontend/src/views/card.ts     |   5 ++
 frontend/src/views/cards.ts    | 114 ++++++++++++++++---------
 internal/leader/leader_test.go |  64 +++++++++++++++
 internal/leader/models.go      |   1 +
 internal/leader/persistence.go |   1 +
 internal/leader/results.go     |  21 +++---
 internal/node/node.go          |  40 +++++++++-
 internal/node/node_test.go     |  65 +++++++++++++++
 13 files changed, 444 insertions(+), 48 deletions(-)
```

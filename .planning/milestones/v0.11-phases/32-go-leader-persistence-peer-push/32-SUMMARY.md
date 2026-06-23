# Phase 32: Go Leader — Persistence & Peer Push — Summary

## Created
- internal/leader/persistence.go — JSON Lines persistence with date-partitioned directories, AppendResults, ReadResults, LoadIntoMemory, FlushLoop
- internal/leader/peerpush.go — Peer notification via HTTP POST /update-peers, PushPeersToAll, ListenForPeerPush
- internal/leader/persistence_test.go — 8 tests covering append, read, flush, load
- internal/leader/peerpush_test.go — 5 tests covering notify URL, payload, push to all

## Modified
- internal/leader/handlers.go — Wired persistence flush loop and peer push into NewLeader
- internal/leader/results.go — Merged dayAggregates into Query90d output

## Code Review
- 14 findings (2 critical, 7 warning, 5 info)
- All critical + warning findings fixed via gsd-code-review-fix
- Fixes: checkPairStatus srcIP filter, flushOnce dedup, RWMutex for config, scanner.Err(), Close() errors, timer leak, dead code removal, HTTP status checks, TOCTOU race

## Tests
- leader package: 38 tests passing
- TestAppendAndReadResults, TestEmptyReadReturnsEmpty, TestAppendPreservesAcrossMultipleCalls
- TestMalformedJSONLineSkippedWithWarning, TestFlushResults, TestLoadIntoMemory, TestLoadIntoMemoryEmptyDataDir
- TestPeerNotifyURL, TestPeerNotifyURLWithNodeURL, TestPeerNotifyURLReturnsEmptyForUnknownNode
- TestNotifyNodeSendsCorrectPayload, TestPushPeersToAllSendsToAllNodes

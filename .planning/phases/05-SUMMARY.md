# Phase 5: Backend — Data Latency Grace Period

## Summary
Extended the NotAvailable threshold from 90s to a configurable 120s grace period, and removed dead `/updateConfig` code from the node server.

## Requirements Delivered
- **DASHD-01**: Added `GRACE_PERIOD` config (default 120s, env `MESH_STATUS_GRACE_PERIOD`). `calculate_status` now uses `max(GRACE_PERIOD, 3 * CHECK_INTERVAL)` as the staleness threshold.

## Additional Changes
- **Cleanup**: Removed dead `handle_update_config` handler and `/updateConfig` route from `node.py` (leader pushes config via `/update-peers`).

## Files Modified
- `mesh_status/config.py` — added `GRACE_PERIOD = 120`, env-configurable
- `mesh_status/status.py` — threshold uses `max(config.GRACE_PERIOD, 3 * config.CHECK_INTERVAL)`
- `node.py` — removed `handle_update_config` and its route registration
- `tests/test_status.py` — updated `test_not_available_status` to use GRACE_PERIOD

## Notes
- 51 tests pass
- Image must be rebuilt (GHA handles push on commit to main)

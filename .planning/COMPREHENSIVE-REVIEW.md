---
phase: comprehensive-review
reviewed: 2026-06-21T12:00:00Z
depth: deep
files_reviewed: 28
files_reviewed_list:
  - node.py
  - register.py
  - mesh_status/__init__.py
  - mesh_status/config.py
  - mesh_status/leader.py
  - mesh_status/models.py
  - mesh_status/persistence.py
  - mesh_status/status.py
  - mesh_status/__main__.py
  - frontend/src/api.ts
  - frontend/src/main.ts
  - frontend/src/types.ts
  - frontend/src/style.css
  - frontend/src/views/bars.ts
  - frontend/src/views/bars.test.ts
  - frontend/src/views/card.ts
  - frontend/src/views/cards.ts
  - frontend/src/views/colors.ts
  - frontend/src/views/colors.test.ts
  - frontend/src/views/day30.ts
  - frontend/src/views/hourly.ts
  - frontend/src/views/matrix.ts
  - frontend/src/views/matrix.test.ts (not found on disk — replaced by mesh.test.ts)
  - frontend/src/views/cards.test.ts (not found on disk — replaced by mesh.test.ts)
  - frontend/src/mesh.ts (not found on disk)
  - frontend/vite.config.ts
  - frontend/tsconfig.json
  - frontend/index.html
  - tests/conftest.py
  - tests/test_data_api.py
  - tests/test_leader_integration.py
  - tests/test_node_integration.py
  - tests/test_persistence.py
  - tests/test_status.py
  - frontend/src/mesh.test.ts (found on disk but not in initial file list)
  - frontend/src/main.test.ts (found on disk but not in initial file list)
findings:
  critical: 5
  warning: 10
  info: 5
  total: 20
status: issues_found
---

# Phase Comprehensive: Code Review Report

**Reviewed:** 2026-06-21T12:00:00Z
**Depth:** deep (cross-file analysis with call-chain tracing)
**Files Reviewed:** 28 source files across Python backend and TypeScript frontend
**Status:** issues_found

## Summary

This comprehensive review covers the entire mesh-status codebase, including the node agent (`node.py`), leader server (`leader.py`), persistence layer (`persistence.py`), status calculation (`status.py`), CLI registration tool (`register.py`), and frontend TypeScript views. The analysis traced call chains across module boundaries, checked type consistency at API interfaces, verified error propagation, and detected shared-state mutation patterns.

**5 critical issues found** — including a data-loss bug in the persistence layer (atomic write destroys previous data), a buffer-retry logic bug that drops results on partial success, race conditions on shared mutable state without synchronization, an unhandled `UnicodeDecodeError` crash path, and overly permissive CORS configuration.

**10 warnings** — including untracked shared state in tests (test pollution), dead code paths, an unusual `proc.wait()`/`communicate()` ordering that risks deadlock, nodes self-checking unnecessarily, and inconsistent status semantics between views.

**5 info items** — including dead TypeScript exports, missing files, and minor style issues.

---

## Critical Issues

### CR-01: Data loss in `_append_results` — atomic replace destroys existing data

**File:** `mesh_status/persistence.py:29-36`
**Issue:** The `_append_results` function opens a `.tmp` file (which is created new or appended to each call), then atomically renames it over the target file. But it **never reads the existing data from the target file**. Each call writes a fresh `.tmp` containing only the new data — all previously persisted data for that date is lost.

```python
# Line 29-36
tmp_path = path.with_suffix(".tmp")
mode = "a" if path.exists() else "w"          # <-- checks if main path exists
with open(tmp_path, mode) as f:               # <-- but writes to .tmp, not main path!
    for item in results:
        f.write(json.dumps(item, default=str) + "\n")
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp_path, path)                    # <-- replaces main file with only new data
```

**Scenario:** Day 1 has 100 results persisted. A new batch of 10 results arrives. `_append_results` writes the 10 results to a new `.tmp` file, then replaces `path` with it. The previous 100 results are gone.

**Fix:** Either remove the atomic-rename pattern (write directly to `path` in append mode), or read existing data from `path`, merge with new data, then atomically write:

```python
# Option A: Direct append (simpler, not atomic but avoids data loss):
with open(path, "a") as f:
    for item in results:
        f.write(json.dumps(item, default=str) + "\n")
    f.flush()
    os.fsync(f.fileno())

# Option B: Atomic merge (preserves existing data):
existing = []
if path.exists():
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                existing.append(json.loads(line))
combined = existing + results
with open(tmp_path, "w") as f:
    for item in combined:
        f.write(json.dumps(item, default=str) + "\n")
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp_path, path)
```

---

### CR-02: Buffer retry logic drops current results on partial success, duplicates on failure

**File:** `node.py:224-236`
**Issue:** The `run()` loop's retry/buffer logic iterates over each batch (buffered + current) individually, submitting them one at a time. If an earlier buffered batch succeeds:
- The `break` exits the loop immediately
- The **current cycle's results (`combined[-1]`) are never submitted and never buffered** — they vanish into the ether.

If a batch submission fails:
- The batch is **appended to the buffer a second time** (it was already there), creating duplicates.

```python
combined = list(result_buffer)  # e.g., [old_cycle_1, old_cycle_2]
combined.append(results)        # e.g., [old_cycle_1, old_cycle_2, current_cycle]

for batch in combined:
    ok = await submit_results(batch, node_ip, leader_url, node_url)
    if ok:
        result_buffer.clear()
        break                  # <-- BUG: current_cycle skipped!
    else:
        result_buffer.append(batch)  # <-- BUG: duplicate if batch was already in buffer!
```

**Trace:** Buffer has `[A]`, current results `[B]`. Combined = `[A, B]`.
1. Submit A → success → `result_buffer.clear()` → break → **B is lost entirely**.

**Trace 2:** Buffer has `[A]`, current results `[B]`.
1. Submit A → fail → `result_buffer.append(A)` → buffer = `[A, A]` (duplicate!)
2. Submit B → fail → `result_buffer.append(B)` → buffer = `[A, A, B]`

**Fix:** Submit all combined checks together as a single payload, not one-batch-at-a-time:

```python
# Flatten all checks into one list
all_checks: list[dict] = []
for batch in combined:
    all_checks.extend(batch)

ok = await submit_results(all_checks, node_ip, leader_url, node_url)
if ok:
    result_buffer.clear()
else:
    result_buffer.append(combined)  # buffer the whole list-of-lists
```

Alternatively, if separate submission is desired (e.g., to minimize payload size), the loop must ensure that the current cycle's results are always submitted or buffered:

```python
combined = list(result_buffer)
combined.append(results)

all_ok = True
for batch in combined:
    ok = await submit_results(batch, node_ip, leader_url, node_url)
    if not ok:
        all_ok = False

if all_ok:
    result_buffer.clear()
else:
    # Re-buffer all combined
    result_buffer.clear()
    for batch in combined:
        result_buffer.append(batch)
```

---

### CR-03: Race condition on shared mutable state (`_results`, `_day_aggregates`) without locks

**File:** `mesh_status/leader.py:137-140` (submit handler), `mesh_status/persistence.py:165-173` (flush loop)

**Issue:** The module-level `_results` dict and `_day_aggregates` dict are shared across multiple concurrent coroutines:

1. **`/submit` route handler** (leader.py:137-140) — writes `_results[node_ip].extend(checks)` without any lock
2. **`flush_loop` background task** (persistence.py:165-173) — reads `_results`, calls `_flush_results` (reads it), then calls `_move_old_to_aggregates` (mutates both `_results` and `_day_aggregates`)
3. **`/data` route** (leader.py:177-309) — iterates over `_results` and `_day_aggregates` to build response
4. **Startup `load_into_memory`** (leader.py:46, persistence.py:110-156) — writes to both stores on leader boot

None of these operations use locks or other synchronization. This is a classic **race condition that can cause**:
- Lost updates (two concurrent submits to the same node_ip)
- Corrupted iteration (`/data` reads while `_move_old_to_aggregates` deletes keys)
- Inconsistent reads

**Fix:** Add an `asyncio.Lock` (or `asyncio.RLock`) to protect all `_results` and `_day_aggregates` accesses:

```python
_results_lock = asyncio.Lock()

# In submit handler:
async with _results_lock:
    if node_ip in _results:
        _results[node_ip].extend(checks)
    else:
        _results[node_ip] = list(checks)

# In flush_loop:
async with _results_lock:
    if _results:
        batch = dict(_results)
        _flush_results(batch)
        cutoff_90h = time.time() - 90 * 3600
        _move_old_to_aggregates(_results, _day_aggregates, cutoff_90h)

# In /data endpoint:
async with _results_lock:
    # read _results and _day_aggregates
```

---

### CR-04: Unhandled `UnicodeDecodeError` in ping output parsing

**File:** `node.py:86`
**Issue:** The ping subprocess stdout is decoded with the default UTF-8 codec. If the ping output contains non-UTF-8 bytes (possible with unusual locales or corrupted network responses), `stdout.decode()` raises `UnicodeDecodeError`, crashing the entire check for that node.

```python
stdout, _ = await proc.communicate()
if proc.returncode == 0:
    match = re.search(r"time=(\d+\.?\d*)\s*ms", stdout.decode())  # <-- can raise!
```

**Fix:** Use `.decode(errors="replace")` to safely handle non-UTF-8 bytes:

```python
stdout_text = stdout.decode(errors="replace")
match = re.search(r"time=(\d+\.?\d*)\s*ms", stdout_text)
```

---

### CR-05: Overly permissive CORS exposes leader API to any website

**File:** `mesh_status/leader.py:22`
**Issue:** `cors(app, allow_origin="*")` allows any website to make cross-origin requests to the leader's API. If a user is logged into the mesh-status UI and visits a malicious site, that site can make API calls to the leader. While there's no authentication (so no session hijacking risk per se), this is a defense-in-depth violation.

**Fix:** Restrict CORS to specific origins (the frontend's actual origin):

```python
cors(app, allow_origin="http://localhost:58080")  # or read from env var
```

Alternatively, for production, serve the frontend from the same origin as the API (which is already the case since the leader serves both), and set a permissive-but-same-origin policy or read allowed origins from `ALLOWED_ORIGINS` env var.

---

## Warnings

### WR-01: `_day_aggregates` not cleared in test fixture — test pollution risk

**File:** `tests/conftest.py:7-17`
**Issue:** The `reset_leader_state` autouse fixture clears `_registry`, `_results`, and `_peers_by_node`, but **not `_day_aggregates`**. Multiple tests in `test_data_api.py` and `test_leader_integration.py` manipulate `_day_aggregates` directly. Without clearing between tests, data from test A can leak into test B, causing spurious interactions.

```python
@pytest.fixture(autouse=True)
def reset_leader_state():
    from mesh_status.leader import _registry, _results, _peers_by_node
    _registry.clear()
    _results.clear()
    _peers_by_node.clear()
    # _day_aggregates is NOT cleared!
```

**Fix:** Also clear `_day_aggregates`:

```python
from mesh_status.leader import _registry, _results, _peers_by_node, _day_aggregates
_registry.clear()
_results.clear()
_peers_by_node.clear()
_day_aggregates.clear()
```

---

### WR-02: `_peers_by_node` is dead code — declared, cleared, never populated

**File:** `mesh_status/leader.py:34`
**Issue:** `_peers_by_node: dict[str, list[str]] = {}` is declared at module scope but is never written to or read by any route handler or internal function. It is only cleared in the test fixture (`conftest.py:13`). Every function that needs peer information uses `_registry` instead.

**Fix:** Remove the variable declaration (line 34), its clear in conftest (line 13), and the unused import if any.

---

### WR-03: `_ensure_data_dir` function is dead code — never called

**File:** `mesh_status/persistence.py:14-17`
**Issue:** The `_ensure_data_dir` function creates the directory tree for a given date but is never called anywhere in the codebase. The directory creation is done inline in `_append_results` (line 28: `path.parent.mkdir(parents=True, exist_ok=True)`).

**Fix:** Either remove the dead function or replace the inline `mkdir` call with `_ensure_data_dir` for consistency.

---

### WR-04: `proc.wait()` called before `proc.communicate()` — risk of deadlock with large stdout

**File:** `node.py:81-84`
**Issue:** The pattern `await proc.wait()` followed by `await proc.communicate()` is unusual and potentially dangerous. `wait()` only waits for process exit — it does not drain the stdout/stderr pipes. If the subprocess writes enough output to fill the pipe buffer, it will block on write. `wait()` will never return because the process is stuck, creating a deadlock.

For `ping -c 1` the output is small (~200 bytes), so this works in practice. However:
1. `communicate()` internally calls `wait()` again, making the first call redundant
2. The pattern is fragile — any change to the ping command flags could increase output

```python
# Current:
await asyncio.wait_for(proc.wait(), timeout=timeout + 0.5)   # <-- waits for exit, doesn't drain pipes
stdout, _ = await proc.communicate()                          # <-- drains pipes, waits for exit (already done)
```

**Fix:** Use `communicate()` with a timeout instead of separate `wait()`:

```python
try:
    stdout, _ = await asyncio.wait_for(
        proc.communicate(), timeout=timeout + 0.5
    )
    if proc.returncode == 0:
        ...
except asyncio.TimeoutError:
    proc.kill()
    await proc.wait()
```

---

### WR-05: Nodes unnecessarily check themselves — waste of resources

**File:** `node.py:209-210` (peers assignment from registration), `mesh_status/leader.py:318-319` (peer dicts includes all registry entries)

**Issue:** When a node registers, the leader returns `_peer_dicts()` which includes all registered nodes — **including the registering node itself**. The node then adds this self-IP to its peer list and will `ping` and `HTTP-check` itself on every check cycle. This wastes network and CPU resources on every node.

The backend `/data` endpoint already filters `src_ip != dst_ip`, but the node agent does not.

**Fix (backend):** `_peer_dicts()` should exclude the requester's IP, but since it's not called per-request, the simpler fix is (node side): Filter out own IP from peers:

```python
# After registration, in run():
shared_state["peers"] = [p for p in data.get("peers", []) if p["ip"] != node_ip]
```

Or in the peer fetch from `/node-list`:

```python
shared_state["peers"] = [p for p in resp.json().get("nodes", []) if p["ip"] != ...]
```

---

### WR-06: Empty bare `except` silences all HTTP check errors

**File:** `node.py:100-101`
**Issue:** The HTTP health-check block catches all exceptions with `except Exception: pass`, discarding all error information. While this prevents check failures from crashing the node, it makes debugging impossible — network timeouts, DNS failures, connection refused errors all produce identical "not OK" results with no logging.

```python
except Exception:
    pass
```

**Fix:** Log the error at debug level to aid troubleshooting without flooding production logs:

```python
except Exception as e:
    logger.debug("HTTP check to %s:%d failed: %s", target_ip, port, e)
```

---

### WR-07: No HTTPS/TLS support — all mesh traffic unencrypted

**Files:** `node.py:96`, `node.py:217`, `leader.py:362-366`
**Issue:** All inter-node communication uses plain HTTP. The node checks targets at `http://{ip}:{port}/healthz`. The leader listens on `0.0.0.0:{port}` with no TLS. The CLI register tool also uses HTTP. While the VPN WAN may provide transport encryption, relying on that is insufficient defense-in-depth.

**Fix:** Add optional HTTPS support — at minimum accept `LEADER_URL` with `https://` scheme and configure Hypercorn/TCP site with TLS cert paths for production deployments.

---

### WR-08: Inconsistent status semantics between 90m view and day/hour views

**Files:** `frontend/src/views/cards.ts:86-99` vs `frontend/src/views/day30.ts:69-76` and `frontend/src/views/hourly.ts:62-69`

**Issue:** The 90m card view's status logic is:
```typescript
if (ping && http) st = "OK";
else if (s.ping_status === "NotAvailable" || s.http_status === "NotAvailable") st = "NotAvailable";
else st = "Pending";
```

The daily/hourly view's status logic is:
```typescript
if (pingUp >= 99.9 && httpUp >= 99.9) return "OK";
if (pingUp < 99.9 && httpUp < 99.9) return "Pending";
return "NotAvailable";   // <-- when one metric is good, one is bad
```

Both return `"NotAvailable"` for degraded-but-active targets, which is semantically wrong — the target IS reachable, just degraded. In the 90m view, `"NotAvailable"` means the node's last check was too old or failed. The 90d view reuses this same string for "one metric is below 99.9%", which is a different meaning. This causes visual confusion (amber dot instead of green for a node that is 99% reachable).

**Fix:** Introduce a distinct status string (e.g., `"Degraded"`) for the mixed-case scenario:

```typescript
function computeStatus(pingUp: number, httpUp: number): string {
  if (pingUp >= 99.9 && httpUp >= 99.9) return "OK";
  if (pingUp >= 99.9 || httpUp >= 99.9) return "Degraded";
  return "Pending";
}
```

And add a corresponding `"Degraded"` entry to `BADGE_MAP` (in `card.ts`) and `STATUS_COLOR`/`STATUS_DOT` (in `matrix.ts`).

---

### WR-09: No input validation in CLI registration tool

**File:** `register.py:27-30`
**Issue:** User input for `node_ip` and `leader_ip` is accepted without any validation — empty strings, malformed IPs, or injection payloads are passed directly into the HTTP request URL.

```python
node_ip = input("Enter node IP: ").strip()
...
url = f"http://{leader_ip}:{args.port}/register"
```

If `leader_ip` contains characters like `..` or whitespace, the URL could be malformed. If `node_ip` is empty, the server will reject it with 400, but the user gets a confusing error.

**Fix:** Validate IP inputs with a basic check before constructing the URL:

```python
import ipaddress

def validate_ip(ip: str) -> bool:
    try:
        ipaddress.ip_address(ip)
        return True
    except ValueError:
        return False

if not validate_ip(node_ip):
    print(f"Invalid node IP: {node_ip}", file=sys.stderr)
    sys.exit(1)
```

---

### WR-10: `test_data_api.py` creates its own test client instead of using the fixture

**File:** `tests/test_data_api.py:13` (and consistently throughout)
**Issue:** Every test method in `TestDataAPI` creates its own Quart test client via `app.test_client()` rather than using the `client` async fixture from `conftest.py`. This means:
1. The `client` fixture's setup/teardown logic is bypassed
2. The `app.test_client()` creates a new client per test without going through pytest fixture lifecycle

```python
# Current pattern in test_data_api.py:
test_client = app.test_client()
resp = await test_client.get("/data?window=90m")

# Fixture pattern (from conftest.py) — not used:
@pytest.fixture
async def client(app):
    async with app.test_client() as c:
        yield c
```

**Fix:** Use the `client` fixture parameter:

```python
class TestDataAPI:
    async def test_data_90h_includes_raw_counts(self, client):
        resp = await client.get("/data?window=90h")
```

---

## Info

### IN-01: Dead TypeScript exports — `fetchData30m`/`fetchData30d` and `Data30mResponse`/`Data30dResponse`

**Files:** `frontend/src/api.ts:35`, `frontend/src/types.ts:64`
**Issue:** These aliases are exported but never imported by any other module in the codebase. They exist solely for backward compatibility but document no consumer. If no consumer exists, they are dead code.

```typescript
export { fetchData90m as fetchData30m, fetchData90d as fetchData30d };
export type { Data90mResponse as Data30mResponse, Data90dResponse as Data30dResponse };
```

**Suggestion:** Remove the aliases. If backward compatibility is needed, add a comment documenting the consumer.

---

### IN-02: Test files for `cards.ts` and `matrix.ts` don't exist at expected paths

**Files:** Listed in review scope: `frontend/src/views/cards.test.ts`, `frontend/src/views/matrix.test.ts` — neither exists on disk.

**Note:** The equivalent tests are consolidated in `frontend/src/mesh.test.ts` (551 lines), which covers `renderCards`, `renderMatrix`, `renderDay30`, and `renderHourly` in a single file. The file was discovered on disk but was not in the initial review file list. If the build pipeline expects per-file test modules, the consolidated file may need splitting.

---

### IN-03: `frontend/src/mesh.ts` listed in scope but does not exist

**File:** `frontend/src/mesh.ts` — not found on disk, not imported anywhere in `main.ts` or other source files.

**Suggestion:** Remove from the project if no longer needed, or create if functionality is pending.

---

### IN-04: `_StopLoop` inherits from `BaseException` — unconventional pattern

**File:** `tests/test_node_integration.py:9-10`
**Issue:** The `_StopLoop` exception used to halt the infinite `node.run()` loop inherits from `BaseException` rather than `Exception`. This means it will propagate through `except Exception:` blocks that would normally catch other exceptions. This is intentional (to not be caught by generic error handlers), but it's unconventional and undocumented.

```python
class _StopLoop(BaseException):
    pass
```

**Suggestion:** Add a comment explaining why `BaseException` is used, or alternatively restructure to use `asyncio.CancelledError` or a sentinel pattern with a timeout.

---

### IN-05: `from typing import Optional` used instead of Python 3.10+ `X | None` syntax

**File:** `mesh_status/models.py:2` (and usages on lines 8, 33)
**Issue:** The project requires `python >= 3.12` (from `pyproject.toml`), but the code uses the older `Optional[str]` syntax instead of the PEP 604 `str | None` syntax.

```python
from typing import Optional

@dataclass
class NodeInfo:
    hostname: Optional[str] = None   # Could be: hostname: str | None = None
```

**Suggestion:** Use `str | None` for consistency with modern Python convention.

---

## Cross-File Analysis Notes

### Import Graph (Call Chains Traced)

```
node.py
  └── mesh_status.config        (config constants)
  └── aiohttp.web               (HTTP server for /healthz, /update-peers)
  └── httpx                     (HTTP client for leader API)

register.py
  └── urllib.request            (HTTP client for registration)

mesh_status/__main__.py
  └── mesh_status.leader        (delegates to leader main())

mesh_status/leader.py
  └── mesh_status.config        (config constants)
  └── mesh_status.models         (NodeInfo dataclass)
  └── mesh_status.persistence    (disk load/load/flush)
  └── mesh_status.status         (calculate_status)
  └── quart, hypercorn, httpx    (HTTP framework, serving, outbound HTTP)

mesh_status/persistence.py
  └── mesh_status.leader (circular import at runtime! via flush_loop line 165)

mesh_status/status.py
  └── mesh_status.config

frontend/src/main.ts
  └── api.ts                    (fetchData90m, fetchData90h, fetchData90d, fetchNodeList)
  └── views/matrix.ts           (renderMatrix)
  └── views/cards.ts            (renderCards)
  └── views/day30.ts            (renderDay30)
  └── views/hourly.ts           (renderHourly)

frontend/src/views/cards.ts
  └── views/card.ts             (cardHtml)
  └── types.ts                  (CheckResult, StatusEntry, ...)

frontend/src/views/card.ts
  └── views/bars.ts             (renderBars)
  └── views/colors.ts           (uptimeColor)

frontend/src/views/bars.ts
  └── views/colors.ts           (uptimeColor)
```

### Circular Import Risk

`persistence.py:165` contains `from mesh_status.leader import _results, _day_aggregates` at function scope (inside `flush_loop`). This avoids the circular import at module level, but it's a code smell — the persistence layer should be self-contained or receive these stores as parameters, not import from the module that imports it.

### Type Consistency at API Boundaries

**Backend → frontend (JSON API):**
- `/data?window=90m` returns `{checks: CheckResult[], statuses: StatusEntry[], timestamp: number}`
- The frontend `Data90mResponse` type matches this correctly.
- `/data?window=90h` returns `{hours: HourData[], window: string}`
- The frontend `Data90hResponse` type matches.
- `/data?window=90d` returns `{days: DayData[], window: string}`
- The frontend `Data90dResponse` type matches.
- `/node-list` returns `{nodes: Array<{ip: string, port: number} | string>}`
- The frontend `NodeListResponse` type matches, but the actual backend returns only `{ip, port}` objects (line 319), never bare strings. The union type is overly permissive but not incorrect.

No type mismatches found at the API boundary.

### Error Propagation Trace

| Function | Errors | Caught? |
|---|---|---|
| `check_node` ping | `asyncio.TimeoutError` | ✓ caught, `proc.kill()` called |
| `check_node` ping stdout decode | `UnicodeDecodeError` | **✗ NOT CAUGHT** (CR-04) |
| `check_node` HTTP | `Exception` | ✓ caught (but silently — WR-06) |
| `submit_results` | `Exception` | ✓ caught, logged |
| `_notify_node` | `Exception` | ✓ caught, logged |
| `run_check_cycle` | All exceptions from gather | ✓ `return_exceptions=True` |
| `handle_update_peers` | JSON decode | ✗ NOT CAUGHT — if `/update-peers` body is not valid JSON, `await request.json()` raises and the handler crashes |
| Main loop | `Exception` | ✓ caught, logged — loop continues |

**Additional finding:** `handle_update_peers` (node.py:151-165) does not handle the case where `request.json()` receives malformed JSON. This would crash the handler. While this is a trusted endpoint (only the leader calls it), a bug in the leader could crash the node's HTTP handler.

---

_Reviewed: 2026-06-21T12:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: deep_

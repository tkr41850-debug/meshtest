# Phase 4 — UI Review

**Audited:** 2026-06-18
**Baseline:** `.planning/phases/04-dashboard/04-UI-SPEC.md` (UI design contract)
**Screenshots:** Not captured (no dev server running on ports 3000, 5173, 8080, 58581, or 58080)
**Tool:** Code-only audit against Streamlit source (`mesh_status/dashboard.py`)

---

## Pillar Scores

| Pillar | Score | Key Finding |
|--------|-------|-------------|
| 1. Copywriting | 3/4 | Expander summary conflates "all down" with "Pending"; 30d expander headers missing summary |
| 2. Visuals | 3/4 | Matrix heading is h5 (too subtle); column order deviates from spec; 30d tab has no matrix |
| 3. Color | 3/4 | Badge text uses `white` vs spec's darker shades; matrix dots are color-only (no tooltip) |
| 4. Typography | 3/4 | Matrix uses 13px default (spec says 14px); matrix heading h5 < 22px section heading |
| 5. Spacing | 3/4 | Badge padding 2px vertical (spec: 4px xs); table margin 12px (not in scale) |
| 6. Experience Design | 2/4 | Refresh timestamp not tied to successful fetch; matrix dots color-only (accessibility); empty data arrays don't hide matrix |

**Overall: 17/24**

---

## Top 3 Priority Fixes

1. **Matrix dots are color-only with no text/tooltip alternative** — Accessibility blocker. Users relying on assistive tech cannot distinguish OK/NotAvailable/Pending in the matrix. Add `title` attributes (e.g., `title="OK"`) to the status dot `<span>` elements in `_render_connectivity_matrix` lines 90-94. This is the single most impactful fix for accessibility compliance.

2. **Refresh indicator timestamp always shows current time, not last successful fetch** — Misleading UX. When the leader is unreachable, the indicator shows "Last update: {now}" even though data hasn't refreshed. The spec explicitly says "timestamp of last successful fetch." Pass the actual data timestamp from `fetch_all_data()` to `_render_refresh_indicator()` and only update it on successful API response.

3. **Expander "Pending" summary incorrectly labels all-down as "Pending"** — Semantic error. Line 145-148: `targets_ok == 0` catches both "all targets are NotAvailable" and "no data for any target." These are distinct states per spec. Change the logic to: if all targets have a status but none are OK → "{X} of {Y} down"; only if all targets truly have no data (zero results returned) → "Pending."

---

## Detailed Findings

### Pillar 1: Copywriting (3/4)

| # | Type | Finding | Location |
|---|------|---------|----------|
| 1.1 | **WARNING** | **Expander `Pending` summary conflates all-down with no-data.** Line 145: `elif targets_ok == 0: summary = "Pending"`. If 3 targets are all `NotAvailable`, this says "Pending" instead of "3 of 3 down." True "Pending" means zero results exist — all-down means data exists but all failed. | `dashboard.py:145-148` |
| 1.2 | **WARNING** | **30-Day View expander headers missing status summary.** Line 189 uses `f"▶ {src_ip}"` only. Spec expander format: `▶ {source_ip} [{status_summary}] — {N} targets`. Both 30m and 30d expanders should follow this format. | `dashboard.py:189` |
| 1.3 | **INFO** | **Empty data arrays don't trigger empty state.** Line 106 only checks `data_30m is None`. If API returns `{"statuses": [], "checks": []}` (valid JSON with empty arrays), the matrix renders with all Pending cells instead of showing "No data available for this time window" and hiding the matrix. | `dashboard.py:106-108` |
| 1.4 | **INFO** | **"No nodes registered" message** (line 103) is not in the spec copy table but is a reasonable addition for the unregistered edge case. | `dashboard.py:103` |

**Spec-matched copy (verified correct):**
- Page title: `mesh-status` ✅ (line 239)
- Tab labels: `30-Minute View`, `30-Day View` ✅ (line 242)
- Status labels: `OK`, `Not Available`, `Pending` ✅ (lines 164-168)
- Self diagonal: `—` (em dash) ✅ (line 86)
- Loading text: `Loading mesh data...` ✅ (line 273)
- Empty state text: `No data available for this time window` ✅ (lines 107, 185)
- Leader unreachable: `⚠ Leader unreachable — showing cached data` ✅ (line 258)
- Refresh indicator: `🔄 Auto-refreshing every 30s | Last update: {HH:MM:SS}` ✅ (lines 231-232)

---

### Pillar 2: Visuals (3/4)

| # | Type | Finding | Location |
|---|------|---------|----------|
| 2.1 | **WARNING** | **"Connectivity Matrix" heading is h5 (#####).** This renders as approximately 14px text — too subtle for the primary visual element of the page. Spec section headings should be 22px/600 (`st.header()` size). Use `st.header()` or `st.markdown("### ...")` for stronger visual hierarchy. | `dashboard.py:134` |
| 2.2 | **WARNING** | **Column order in expander detail rows doesn't match spec.** Implementation: `[Target, Status, Ping, HTTP, Last Check]` with ratios `[2, 1, 1, 1, 1]`. Spec: `[Status, Target IP, Ping, HTTP, Last Check]` with ratios `[1, 2, 2, 2, 1]`. Status (the most important indicator) should be first. | `dashboard.py:151,175` vs `04-UI-SPEC.md:150-158` |
| 2.3 | **WARNING** | **30-Day View has no matrix and no section heading.** 30m tab explicitly labels `Connectivity Matrix` as a named section (line 134). 30d tab jumps directly to expanders. This creates visual inconsistency. Either add a `Daily Uptime Overview` heading or match the 30m structure. | `dashboard.py:183-225` |
| 2.4 | **INFO** | **Matrix uses raw HTML table** instead of `st.table()` or `st.dataframe()`. This is functional and necessary for the colored dot rendering, but deviates from the spec component choice. | `dashboard.py:58-98` |

**Positive notes:**
- Matrix is the clear focal point ✅
- Horizontal scroll enabled via `overflow-x: auto` ✅
- Sorted rows/columns (ascending IP) ✅
- Self-to-self diagonal uses `—` ✅

---

### Pillar 3: Color (3/4)

| # | Type | Finding | Location |
|---|------|---------|----------|
| 3.1 | **WARNING** | **Badge text color uses `white` instead of spec's darker shades.** Spec says OK text should be `#166534` (green-800), NotAvailable text should be `#92400e` (amber-800), Pending text should be `#4b5563` (gray-600). All use `color:white` in implementation. While white provides good contrast, this is a spec deviation. | `dashboard.py:164-168` |
| 3.2 | **WARNING** | **Matrix dots are color-only with no tooltip/text alternative.** The `<span>` elements for status dots (lines 90-94) have no `title` attribute. Color-only indication violates WCAG 1.4.1 and the spec's own "No color-only indication" rule. Add `title="OK"`, `title="Not Available"`, `title="Pending"` to the respective spans. | `dashboard.py:90-94` |
| 3.3 | **INFO** | **30-Day View "no data" badge renders as text only.** Line 197: `<span style="color:#9ca3af;">—</span>` — no background badge. Spec implies a badge rendering (`#9ca3af` background for no-data case), not just colored text. | `dashboard.py:197` |
| 3.4 | **INFO** | **Warning banner uses `st.warning()` default styling.** The spec says use Streamlit default warning styling, so this is compliant ✅. | `dashboard.py:258` |

**Spec-matched colors (verified correct):**
- OK dot: `#22c55e` ✅ (line 90)
- NotAvailable dot: `#f59e0b` ✅ (line 92)
- Pending dot: `#9ca3af` ✅ (line 94)
- Self `—`: `#9ca3af` ✅ (line 86)
- Matrix header bg: `#f3f4f6` ✅ (line 64, 71)
- Matrix header text: `#374151` ✅ (line 64, 71)
- Empty state text: `#6b7280` ✅ (lines 103, 107, 185, 225)
- Detail latency text: `#6b7280` ✅ (lines 178-180)
- 30d ≥99%: `#22c55e` ✅ (line 211)
- 30d ≥95%: `#f59e0b` ✅ (line 213)
- 30d <95%: `#ef4444` ✅ (line 215)

---

### Pillar 4: Typography (3/4)

| # | Type | Finding | Location |
|---|------|---------|----------|
| 4.1 | **WARNING** | **Matrix table base font-size is 13px.** Line 60: `font-size: 13px`. Spec says table headers should be 14px (line 69 of UI-SPEC), and monospace IPs should be 14px (line 68 of UI-SPEC). Bump to 14px for spec compliance. | `dashboard.py:60` |
| 4.2 | **WARNING** | **"Connectivity Matrix" heading is h5 (#####).** Streamlit renders `#####` at approximately 14px. Spec says section headings should be 22px/600 (`st.header()`). The weak heading undermines the matrix's visual prominence as the primary page element. | `dashboard.py:134` |
| 4.3 | **WARNING** | **Matrix status dot size is 18px.** The `\u25cf` (●) character at 18px is larger than necessary for a 48px-min-width cell. At default line-height this may cause vertical overflow or cell height inconsistencies. Consider 14px-16px for better cell fit. | `dashboard.py:90-94` |
| 4.4 | **INFO** | **Expander detail rows use 14px monospace for IPs** ✅ — matches spec. | `dashboard.py:176` |
| 4.5 | **INFO** | **Badge labels use 12px** ✅ — matches spec "12px for label text." | `dashboard.py:164-168` |

**Spec-matched typography:**
- Streamlit default system-ui font cascade ✅ (no custom fonts loaded)
- `st.title()`, body text, caption sizes all inherit Streamlit defaults ✅

---

### Pillar 5: Spacing (3/4)

| # | Type | Finding | Location |
|---|------|---------|----------|
| 5.1 | **WARNING** | **Badge inner padding is 2px vertical, 8px horizontal.** Spec says xs token (4px) for inner padding. Vertical padding of 2px is below the minimum spacing token. Change to `padding: 4px 8px`. | `dashboard.py:164-168` |
| 5.2 | **WARNING** | **Table bottom margin is 12px.** Not in the spec's spacing scale (xs=4, sm=8, md=16, lg=24). Should be either 8px (sm) or 16px (md). | `dashboard.py:59` |
| 5.3 | **WARNING** | **Column width ratios don't match spec.** Expander details use `[2, 1, 1, 1, 1]` (30m view line 151) and `[1.5, 1, 1, 1, 1]` (30d view line 195). Spec says `[1, 2, 2, 2, 1]` — Status badge (narrowest) should be first, Target IP (widest) should be second. | `dashboard.py:151,195` vs `04-UI-SPEC.md:150` |
| 5.4 | **INFO** | **Matrix cell padding:** `padding: 4px 8px` ✅ — matches xs/sm tokens. | `dashboard.py:63,70,78,83` |

---

### Pillar 6: Experience Design (2/4)

| # | Type | Finding | Location |
|---|------|---------|----------|
| 6.1 | **BLOCKER** | **Refresh indicator timestamp always shows `dt.now()`, not last successful fetch.** Line 229: `dt.now().strftime("%H:%M:%S")`. When leader is unreachable, the timestamp still updates, making stale data appear fresh. Spec says "updated on each successful fetch." Pass a `last_successful_timestamp` through `fetch_all_data()` and only render the current time when the fetch succeeded. | `dashboard.py:228-235` |
| 6.2 | **BLOCKER** | **Matrix dots are color-only with no title/tooltip.** As noted in Color (3.2), the matrix's colored dots have no text alternative. This violates WCAG Success Criterion 1.4.1 (Use of Color) and the spec's explicit accessibility requirement. Add `title="OK"` (etc.) attributes to each status dot `<span>`. | `dashboard.py:90-94` |
| 6.3 | **WARNING** | **Empty data response doesn't hide the matrix.** Line 106 only checks `data_30m is None`. If the API returns `{"statuses": [], "checks": []}`, the code proceeds to render a matrix with all-Pending cells and expanders with all-Pending summaries. Spec says "Matrix not rendered (empty state replaces it) — Expanders not rendered." Add an explicit check for empty `statuses`/`checks` arrays. | `dashboard.py:106-108, 183-186` |
| 6.4 | **WARNING** | **30-Day View expander headers missing status summary.** Same copy issue as 1.2, but with UX impact: users can't see at a glance which sources have issues in the 30d view without opening every expander. | `dashboard.py:189` |
| 6.5 | **INFO** | **`leader_ok` parameter passed to `_render_refresh_indicator` but unused.** The function signature accepts `leader_ok` (line 228), and it's passed on line 267, but never referenced in the function body. The refresh indicator is identical regardless of leader state. Either use it to modify the indicator text during outages (e.g., "Cached data — last successful: 14:22:11") or remove the parameter. | `dashboard.py:228,267` |
| 6.6 | **INFO** | **No explicit `st.session_state["active_tab"]` tracking.** The spec recommends session_state tracking for tab index. Streamlit manages tab state internally when `st.tabs()` is outside the fragment, so this works, but explicit tracking would provide more resilience. | `dashboard.py:242` |

**Positive notes:**
- Tabs created outside fragment ✅ — persist across fragment reruns (fixes WR-02)
- `@st.cache_data(ttl=25)` ensures fresh fetch each cycle ✅
- `time.sleep(30)` + `st.rerun(scope="fragment")` for auto-refresh ✅
- Leader unreachable warning preserves cached data ✅
- Initial load wrapped in `st.spinner` ✅
- Fragment rerun is silent (no spinner on refresh) ✅
- Error logging to stderr via logger ✅

---

## Registry Safety

Not applicable — project uses pure Streamlit built-in components. No shadcn/third-party component registries detected. `components.json` does not exist.

---

## Files Audited

| File | Lines | Role |
|------|-------|------|
| `mesh_status/dashboard.py` | 274 | Implemented frontend (audited) |
| `.planning/phases/04-dashboard/04-UI-SPEC.md` | 339 | UI design contract (ground truth) |
| `.planning/phases/04-dashboard/CONTEXT.md` | 80 | User decisions and context |
| `mesh_status/status.py` | 65 | Status logic (data model reference) |
| `mesh_status/config.py` | 7 | Configuration constants |
| `mesh_status/models.py` | 34 | Data models (CheckResult, etc.) |
| `README.md` | 23 | Deployment documentation |

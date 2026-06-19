# Phase 7b: HTML Rendering Fix - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix raw HTML code rendering in expander detail cards. The closing `</div>` tag of the card HTML renders as inline code instead of being processed as HTML.

</domain>

<decisions>
## Implementation Decisions

### Root Cause Analysis
- `st.markdown(card, unsafe_allow_html=True)` renders multi-line HTML f-strings
- Python-Markdown parser can misinterpret block-level HTML tags (`<div>`, `</div>`) on their own lines when inside nested Streamlit contexts (expanders)
- The `</div>` at the end of the card gets treated as inline code rather than raw HTML

### Fix Approach
- Refactor `_render_detail_card` to build HTML string without internal newlines (empty-string join of parts)
- Same pattern as `_render_connectivity_matrix` which renders correctly
- No newlines between block-level HTML elements eliminates parser ambiguity
- Card visual appearance preserved identically

### OpenCode's Discretion
- CSS style string compacting (multi-line → single-line) to fit the no-newline approach

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_render_connectivity_matrix()` in dashboard.py:59-99 — successfully uses HTML parts approach
- `_render_detail_card()` in dashboard.py:131-173 — currently uses multi-line f-string

### Established Patterns
- HTML parts joined with `"".join(parts)` prevents Markdown parser ambiguity
- All CSS inline (no external stylesheets)

### Integration Points
- Only `_render_detail_card` needs changes
- Callers and other helpers unaffected

</code_context>

<specifics>
## Specific Ideas

- Build the card HTML the same way as the connectivity matrix: list of string parts → `"".join()`
- Keep code readable with one part per line
- No visual changes to the card — just the internal HTML construction

</specifics>

<deferred>
## Deferred Ideas

- None

</deferred>

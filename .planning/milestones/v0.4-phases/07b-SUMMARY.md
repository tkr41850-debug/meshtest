# Phase 7b: HTML Rendering Fix

## Summary
Fixed raw HTML code rendering in expander detail cards by refactoring HTML construction from multi-line f-string to a parts-list join pattern (no internal newlines), preventing Python-Markdown parser from splitting block-level HTML tags into separate blocks.

## Root Cause
`st.markdown(card, unsafe_allow_html=True)` with a multi-line f-string containing block-level HTML tags (`<div>`, `</div>`) on separate lines could cause Python-Markdown's HTML block parser to misinterpret closing tags as inline code when inside nested Streamlit expander contexts. The `</div>` closing tag on its own line was rendered as inline code (backtick-wrapped) instead of being processed as HTML.

## Items Delivered

### Item 1: HTML card rendering fix
- Refactored `_render_detail_card` from multi-line f-string to parts-list with `"".join()`
- Same pattern as `_render_connectivity_matrix` (which worked correctly)
- No newlines between block-level HTML elements eliminates parser ambiguity
- No visual changes to card appearance

## Files Modified
- `mesh_status/dashboard.py`

## Verification
- All 53 tests pass (no regressions)

# Phase 7b: HTML Rendering Fix - Plan

## Tasks

### Task 1: Refactor `_render_detail_card` HTML construction
- Change from multi-line f-string to parts list with `"".join()`
- No newlines between block-level HTML elements
- Preserve all visual styling and layout

## Files Modified
- `mesh_status/dashboard.py`

## Verification
- Run existing tests: `python -m pytest tests/ -v`
- Verify no regressions

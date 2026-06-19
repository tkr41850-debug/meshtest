# Phase 8: Frontend Scaffold + Build Pipeline - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning

<domain>
## Phase Boundary

Initialize a Vite + TypeScript + Tailwind CSS frontend project in `frontend/`, set up Vitest for testing, update the Docker build pipeline for multi-stage Node→Python builds, update Quart to serve static files, and remove Streamlit from the startup process.

</domain>

<decisions>
## Implementation Decisions

### Project Structure
- Frontend lives in `frontend/` at repo root
- Built output goes to `frontend/dist/`
- Leader (Quart) serves `dist/` as static files from port 58080
- Frontend uses relative API URLs (same-origin)

### Technology Choices
- Vite with vanilla TypeScript (not React — lightweight, no framework overhead)
- Tailwind CSS via PostCSS for styling
- Vitest for testing
- ESLint + Prettier configured

### Docker Build
- Multi-stage build: Node.js stage builds frontend, Python stage copies `dist/`
- No need for `node_modules` in the final image — only static files

### Leader Changes
- Quart adds a route to serve files from the `dist/` directory
- API routes remain unchanged
- Streamlit startup removed from `entrypoint.sh`

### OpenCode's Discretion
- Exact Tailwind configuration (colors, fonts) matching existing v0.4 design
- ESLint ruleset
- Dev server proxy setup (if needed for local dev without leader)

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `mesh_status/dashboard.py` — source of truth for the three views to be ported
- `Dockerfile.leader` — current single-stage Python build
- `entrypoint.sh` — current Hypercorn + Streamlit startup

### Established Patterns
- Port 58080 for leader API
- UV for Python dependency management
- Color scheme: green `#22c55e`, amber `#f59e0b`, red `#ef4444`

### Integration Points
- Quart static route for `./dist`
- Frontend fetches from `/data`, `/node-list`, `/livez` endpoints

</code_context>

<specifics>
## Specific Ideas

- Use npm (not yarn/pnpm) for consistency
- `npm run dev` should proxy API requests to the leader for local development
- Docker build should use `node:22-alpine` for the build stage

</specifics>

<deferred>
## Deferred Ideas

- None

</deferred>

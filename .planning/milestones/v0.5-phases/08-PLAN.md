# Phase 8: Frontend Scaffold + Build Pipeline - Plan

## Tasks

### Task 1: Initialize Vite + TS + Tailwind + Vitest
- `npm create vite@latest frontend/ -- --template vanilla-ts`
- Install Tailwind CSS, PostCSS, autoprefixer
- Configure `tailwind.config.js`, `postcss.config.js`
- Install Vitest, add `test` script
- Add stub test

### Task 2: Project tooling
- Enable `strict: true` in `tsconfig.json`
- Install ESLint + Prettier, create configs
- Add `typecheck`, `lint`, `format` scripts

### Task 3: Tailwind design system
- Configure colors matching v0.4: `mesh-green`, `mesh-amber`, `mesh-red`, `mesh-gray`
- Configure fonts: monospace for IPs, system font for body

### Task 4: Quart static file serving
- Add `/_static/` route or serve `dist/` at root in `mesh_status/leader.py`
- Ensure API routes take priority over static routes

### Task 5: Update entrypoint.sh
- Remove Streamlit startup block
- Hypercorn starts and serves both API + static

### Task 6: Update Dockerfile.leader
- Multi-stage build:
  - Stage 1: `node:22-alpine`, copy `frontend/`, `npm ci && npm run build`
  - Stage 2: `python:3.12-slim`, copy `dist/` from stage 1

### Task 7: Update compose.yml
- Remove port 58581 mapping
- Update any remaining Streamlit references

### Task 8: Update GHA workflow
- Add frontend build step

### Task 9: Verify pipeline
- `docker build` succeeds
- Stub page loads on port 58080
- All existing Python tests pass

## Files Created
- `frontend/` — complete Vite project (multiple files)
- `.github/workflows/docker-publish.yml` — updated with frontend build

## Files Modified
- `mesh_status/leader.py` — add static serving
- `entrypoint.sh` — remove Streamlit
- `Dockerfile.leader` — multi-stage build
- `compose.yml` — remove port 58581

## Verification
- Run: `docker build -f Dockerfile.leader .`
- Run: `python3 -m pytest tests/ -v`
- Visit: `http://localhost:58080` after docker compose up

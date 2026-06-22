.PHONY: ci test test-frontend test-backend test-integration lint format format-check build check typecheck-frontend

# ── Full CI pipeline (runs everything CI would check) ─────────────
ci: lint format-check test-backend test-frontend build

# ── Tests ──────────────────────────────────────────────────────────
test-backend:
	uv run --extra dev pytest tests/ -v

test-integration:
	uv run --extra dev pytest spec/ -v

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend

# ── Lint & Format ──────────────────────────────────────────────────
lint:
	uv run --extra dev ruff check .

format-check:
	uv run --extra dev ruff format --check .

format:
	uv run --extra dev ruff format .

# ── Build ──────────────────────────────────────────────────────────
build:
	cd frontend && npm run build

typecheck-frontend:
	cd frontend && npx tsc --noEmit

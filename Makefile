.PHONY: ci test test-frontend test-backend test-go test-integration lint format-check format build check typecheck-frontend

ci: lint format-check test-backend test-frontend test-go build

test-backend:
	uv run --extra dev pytest tests/ -v

test-go:
	go test ./...

test-integration:
	uv run --extra dev pytest spec/ -v

test-frontend:
	cd frontend && npm test

test: test-backend test-frontend test-go

lint:
	uv run --extra dev ruff check .

format-check:
	uv run --extra dev ruff format --check .

format:
	uv run --extra dev ruff format .

build:
	cd frontend && npm run build

typecheck-frontend:
	cd frontend && npx tsc --noEmit

---
phase: 20-docker-ci
reviewed: 2026-06-21T12:00:00Z
depth: standard
files_reviewed: 6
files_reviewed_list:
  - .github/workflows/ci.yml
  - Dockerfile.ci-test
  - Makefile
  - pyproject.toml
  - .gitignore
  - uv.lock
findings:
  critical: 0
  warning: 3
  info: 3
  total: 6
status: issues_found
---

# Phase 20: Code Review Report — Docker & CI

**Reviewed:** 2026-06-21T12:00:00Z
**Depth:** standard
**Files Reviewed:** 6
**Status:** issues_found

## Summary

Reviewed 6 files covering CI workflow (`.github/workflows/ci.yml`), test container definition (`Dockerfile.ci-test`), build tooling (`Makefile`, `pyproject.toml`), ignore rules (`.gitignore`), and dependency lock (`uv.lock`). No blockers found, but there are 3 warnings and 3 info items.

The CI pipeline is functionally correct: tests 01-03 run in isolation via ephemeral Docker containers, the lint-format job validates code style, and the Makefile provides the correct targets. The most notable issues are missing `.PHONY` declarations in the Makefile (can cause targets to silently skip) and the `uv.lock` being overly large for review purposes (though this is by design in uv).

## Warnings

### WR-01: Makefile missing `.PHONY` for `format-check`, `test`, `typecheck-frontend`

**File:** `Makefile:1,10,12,19,29`
**Issue:** Three targets (`format-check`, `test`, `typecheck-frontend`) are not declared `.PHONY`. If a file or directory with any of these names is ever created in the project root, the corresponding `make` target will silently fail to run because Make considers the target "up to date".

Additionally, `.PHONY: check` is declared on line 1 but no `check:` target exists in the Makefile — this is a dead declaration that does nothing but adds confusion.

**Fix:**
```makefile
.PHONY: ci test-frontend test-backend lint format format-check test build typecheck-frontend
```

### WR-02: `.dockerignore` missing `frontend/node_modules/` and `frontend/dist/`

**File:** `Dockerfile.ci-test:18` (affected by `.dockerignore` gaps)
**Issue:** The `.dockerignore` has `node_modules/` only at the root level pattern. Docker's `.dockerignore` uses Go `filepath.Match` semantics — `node_modules/` only matches `./node_modules/` in the build context root, NOT `frontend/node_modules/`. Similarly, `dist/` only matches `./dist/` at root, not `frontend/dist/`.

If developers run `npm install` locally before building the Docker image, `frontend/node_modules/` (hundreds of MB) gets copied into the image via `COPY . /repo`. This bloats the image and adds unnecessary I/O during `docker build`. While `install.sh` runs `npm ci` which overwrites these files, the wasted copy still occurs.

**Fix:** Add to `.dockerignore`:
```
**/node_modules/
frontend/node_modules/
frontend/dist/
```

### WR-03: `.gitignore` missing platform-agnostic cleanup patterns for non-frontend directories

**File:** `.gitignore`
**Issue:** The root `.gitignore` does not include `.env`, `*.swp`/`*.swo` (vim swap), or `*.log` for non-frontend paths. The `frontend/.gitignore` covers the frontend subtree, but files created at the repo root (e.g., server crash logs, editor swap files, or a `.env` file placed for testing) would not be ignored.

**Fix:**
```
.env
*.sw?
*.log
```

## Info

### IN-01: uv installed without version pinning

**File:** `Dockerfile.ci-test:14`, `.github/workflows/ci.yml:85`
**Issue:** Both the Docker image and the CI lint-format job install uv via `curl https://astral.sh/uv/install.sh | sh` without pinning a specific version. This means CI behavior can change without notice when a new uv version is released. While uv maintains backward compatibility, this is a reproducibility concern.

To pin uv, the CI job can use a specific tag or SHA:
```bash
curl -LsSf https://astral.sh/uv/0.6.0/install.sh | sh
```
Or use the `UV_VERSION` environment variable supported by the installer.

### IN-02: No explicit ruff lint rules configured in `pyproject.toml`

**File:** `pyproject.toml:22-24`
**Issue:** The `[tool.ruff]` section only sets `line-length` and `target-version`. No rule selection (`select`/`ignore`) is specified, so ruff defaults to its built-in rule set (`E`, `F`, `I`, `N`, `W`, `UP`, `B`, `A`, `C4`, `DTZ`, `T10`, `ISC`, `PLC`, `PLE`, `PLR`, `PLW`, `RUF`). While the defaults are reasonable, different versions of ruff may change the default rule set, causing CI to fail after an update even when no code changed.

**Fix:**
```toml
[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP", "B", "A", "C4", "PLC", "PLE", "PLR", "PLW", "RUF"]
```

Or pin ruff in `pyproject.toml`:
```
ruff = "==0.11.2"
```

### IN-03: Report `uv.lock` not reviewable at standard depth

**File:** `uv.lock`
**Issue:** The `uv.lock` file is a generated machine-readable lock file (54KB+). At standard depth it was not substantively reviewed beyond verifying `requires-python` consistency with `pyproject.toml`. The file format, version, and first few packages are valid. No dependency versions conflict with `pyproject.toml` requirements. This file is best validated programmatically (e.g., `uv lock --check` in CI), not via manual review.

---

_Reviewed: 2026-06-21T12:00:00Z_
_Reviewer: OpenCode (gsd-code-reviewer)_
_Depth: standard_

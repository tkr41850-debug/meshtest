---
wave: 1
id: 20-plan-01-ci-test
objective: Create Docker CI test for install and start flow
depends_on:
  - 18-plan-01-install-sh
  - 19-plan-01-start-sh
files_modified:
  - Dockerfile.ci-test
  - .github/workflows/ci.yml
  - deploy/install.sh
  - pyproject.toml
requirements_addressed:
  - TEST-01
  - TEST-02
  - TEST-03
autonomous: true
must_haves:
  truths:
    - "CI builds a fresh container from Ubuntu 24.04, runs install.sh -y, and install completes"
    - "CI runs install.sh -y with MESH_STATUS_VERSION=v0.8 and verifies version pinning"
    - "CI validates start.sh --leader launches and /livez returns healthy"
    - "install.sh supports MESH_STATUS_LOCAL_SOURCE env var for testing from local repo"
    - "pyproject.toml includes setuptools.packages.find to avoid multi-package discovery"
  artifacts:
    - path: "Dockerfile.ci-test"
      provides: "Reproducible test environment (Ubuntu 24.04 + git + curl + Node 22 + uv)"
    - path: ".github/workflows/ci.yml"
      provides: "GitHub Actions workflow: test-install (3 tests) + lint-format"
    - path: "deploy/install.sh"
      provides: "Added MESH_STATUS_LOCAL_SOURCE env var for local source installs"
    - path: "pyproject.toml"
      provides: "Fixed setuptools auto-discovery issue with multiple top-level packages"
  key_links:
    - from: "Dockerfile.ci-test"
      to: ".github/workflows/ci.yml"
      via: "test-install job builds from Dockerfile.ci-test"
    - from: ".github/workflows/ci.yml (TEST-01)"
      to: "deploy/install.sh"
      via: "runs install.sh -y with MESH_STATUS_LOCAL_SOURCE"
    - from: ".github/workflows/ci.yml (TEST-03)"
      to: "start.sh"
      via: "after install, runs start.sh --leader and curls /livez"
---
# Plan 20-01: Docker CI Testing

## Tasks

### Task 1: Create Dockerfile.ci-test

<read_first>
- Dockerfile.leader (existing patterns, uses python:3.12-slim)
</read_first>

<files>
Dockerfile.ci-test
</files>

<action>
Create `Dockerfile.ci-test`:
- Base: `ubuntu:24.04`
- Install `git`, `curl`, `ca-certificates` via apt
- Install Node.js 22 from NodeSource (required for Vite 8 frontend build)
- Install `uv` via the Astral install script to `/usr/local/bin`
- Create `testuser` user
- `COPY . /repo` — embed repo source for CI self-containment
- Set `UV_LINK_MODE=copy` for uv compatibility
- Default USER testuser with WORKDIR /home/testuser
</action>

<done>
- `docker build -t mesh-test -f Dockerfile.ci-test .` succeeds
- Container has: git, curl, uv, node, npm
</done>

<verify>
docker build -t mesh-test -f Dockerfile.ci-test .
</verify>

### Task 2: Create GitHub Actions workflow

<read_first>
- (no existing .github/workflows/ — first CI file)
</read_first>

<files>
.github/workflows/ci.yml
</files>

<action>
Create `.github/workflows/ci.yml` with:

**Trigger:** push to main, PR to main

**Job: test-install**
Runs-on: ubuntu-latest

Steps:
1. Checkout repo (`actions/checkout@v4`)
2. Build test container (`docker build -t mesh-test -f Dockerfile.ci-test .`)
3. TEST-01: `docker run mesh-test bash -c 'MESH_STATUS_LOCAL_SOURCE=/repo bash /repo/deploy/install.sh -y'` — verify install directory and sentinel file
4. TEST-02: same but with `MESH_STATUS_VERSION=v0.8` — verify version pinning
5. TEST-03: `docker run -d` with leader, poll `/livez` up to 30s via `docker exec curl`

**Job: lint-format** (standard Python CI hygiene)
Steps:
1. Checkout, install uv, setup Python 3.12
2. uv sync
3. ruff format --check, ruff check, pyright

**Health check approach for TEST-03:**
```
docker run -d --name mesh-leader mesh-test bash -c '
  MESH_STATUS_LOCAL_SOURCE=/repo bash /repo/deploy/install.sh -y
  cd ~/.local/meshtest
  exec bash start.sh --leader
'
loop over 10 attempts × 3s sleep:
  docker exec mesh-leader curl -sf http://localhost:58080/livez
```
</action>

<done>
- Workflow YAML is valid
- Each test and lint job fails independently if any step fails
</done>

<verify>
python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"
</verify>

### Task 3: Fix install.sh for local source testing

<read_first>
- deploy/install.sh (existing clone flow)
</read_first>

<files>
deploy/install.sh
</files>

<action>
Add `MESH_STATUS_LOCAL_SOURCE` env var support:

```bash
MESH_STATUS_LOCAL_SOURCE="${MESH_STATUS_LOCAL_SOURCE:-}"
```

In the clone/install block, add a branch between "existing install" and "clone":

```bash
elif [ -n "$MESH_STATUS_LOCAL_SOURCE" ]; then
    echo "Copying mesh-status from $MESH_STATUS_LOCAL_SOURCE to $MESH_STATUS_HOME..."
    mkdir -p "$(dirname "$MESH_STATUS_HOME")"
    rm -rf "$MESH_STATUS_HOME"
    cp -a "$MESH_STATUS_LOCAL_SOURCE" "$MESH_STATUS_HOME"
    cd "$MESH_STATUS_HOME"
```

Also add to `usage()` output.
</action>

<done>
- `MESH_STATUS_LOCAL_SOURCE=/repo bash install.sh -y` installs from local copy
- Sentinel file written correctly
- Frontend builds from local copy
</done>

<verify>
docker run --rm mesh-test bash -c 'MESH_STATUS_LOCAL_SOURCE=/repo bash /repo/deploy/install.sh -y'
</verify>

### Task 4: Fix pyproject.toml setuptools auto-discovery

<read_first>
- pyproject.toml (missing packages.find)
</read_first>

<files>
pyproject.toml
</files>

<action>
Add before `[build-system]`:

```toml
[tool.setuptools.packages.find]
include = ["mesh_status*"]
```

This prevents `uv sync` from failing with "Multiple top-level packages discovered" when building from a fresh clone/copy (deploy/, frontend/, mesh_status/ all detected).
</action>

<done>
- `uv sync` succeeds from fresh copy of repo
- No "Multiple top-level packages" error
</done>

<verify>
docker run --rm mesh-test bash -c 'MESH_STATUS_LOCAL_SOURCE=/repo bash /repo/deploy/install.sh -y'
</verify>

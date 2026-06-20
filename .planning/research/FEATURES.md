# Feature Research: Install & Start Scripts

**Domain:** curl-pipe-bash install scripts + unified start runner for Python mesh app
**Researched:** 2026-06-20
**Confidence:** HIGH (verified against real-world install scripts: rustup, nvm, pyenv-installer; plus init script patterns and FHS standards)

## Feature Landscape

### Table Stakes (Users Expect These)

Features users assume exist. Missing these = install script feels broken.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Prerequisite check** | Script must validate `uv` and `git` exist before proceeding | LOW | `command -v uv` and `command -v git`; bail with clear message pointing to install docs for each |
| **Idempotent re-install** | Running install.sh twice should update, not error | MEDIUM | Detect existing install dir → `git pull` or `git checkout` tag instead of fresh clone. nvm pattern: `if [ -d "$INSTALL_DIR/.git" ]; then ... update; fi` |
| **Version pinning** | User must be able to install a specific release tag | MEDIUM | Accept `MESH_STATUS_VERSION= v0.8.0` env var or `--version` flag. Default to latest tag from GitHub API or main branch |
| **Non-interactive mode** | CI/CD and automation need `-y` / `--yes` flag | LOW | Skip confirmation prompts, use defaults. All flags must work without stdin (since pipe mode has no stdin) |
| **`--help` flag** | Standard discoverability | LOW | Print usage: options, env vars, examples |
| **Success banner** | User needs to know it worked and what to do next | LOW | Print install path, start command, URL for dashboard. nvm/rustup both do this |
| **`start.sh` basic start** | `start.sh --leader` runs the leader process | LOW | Launch `uv run python -m mesh_status` with proper working directory and logging |
| **`start.sh` basic node start** | `start.sh --node` runs the node agent | LOW | Launch `uv run python node.py --leader-url ... --node-url ...` |
| **Log output to file** | Daemon output must persist, not disappear with terminal | LOW | Redirect stdout/stderr to `$INSTALL_DIR/var/leader.log` or similar |
| **Install directory convention** | Users expect a standard location | LOW | Default to `~/.local/opt/mesh-status` (XDG-compatible, no sudo). Allow override via `MESH_STATUS_HOME` |
| **Config file bootstrapping** | First install must create a usable config | MEDIUM | Generate `.env` or config file with sensible defaults; print instructions for override |
| **Clean uninstall** | Users must be able to remove the install cleanly | MEDIUM | `start.sh --uninstall` or separate script. Remove install dir, optionally remove config, print PATH cleanup instructions |

### Differentiators (Nice-to-Have for v0.8)

Features that improve the experience but aren't strictly necessary for v0.8.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Offline detection** | Users on unreliable connections get actionable feedback | MEDIUM | Check connectivity to GitHub before attempting clone. `curl -I` to github.com with timeout |
| **Progress indicators** | Long operations need visible feedback | MEDIUM | `git clone --progress` can be verbose; `uv sync` outputs its own progress |
| **Pre-built frontend** | Skip Node.js/npm build requirement for install | MEDIUM | Ship pre-built frontend in release archive. NPM + Vite build is heavy for an install step |
| **Systemd service unit** | Production deployments need auto-start on boot | HIGH | Generate `mesh-status-leader.service` and `mesh-status-node@.service` unit files during install |
| **Health check after start** | Verify process actually started and responds | MEDIUM | After launching leader, poll `GET /livez` with timeout before reporting success |
| **`start.sh config wizard`** | Interactive first-run setup for config | MEDIUM | Needs `bash -c "$(curl ...)"` style (pipe mode has no stdin). Has implications for curl-pipe-bash mode |
| **Update check** | Notify user when new version is available | LOW | On `start.sh`, check latest GitHub tag vs installed version. Non-blocking warning |
| **Docker-based install verification** | Automated CI test of install.sh | HIGH | Docker-in-Docker test: `FROM ubuntu:24.04`, install uv+git, run install.sh, verify binaries, run start.sh, healthcheck. See below for complexity details |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem good but create problems for a curl-pipe-bash installer.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **`sudo` auto-escalation** | Simpler UX, no permission errors | **Security risk** — piped scripts should NEVER auto-sudo. Users lose control. codecov breach (2021) is canonical example | Fail with clear message: "Install as non-root to ~/.local/opt or run sudo MESH_STATUS_HOME=/opt ./install.sh" |
| **Modify shell rc files** | Make `start.sh` available in PATH automatically | **User trust issue** — modifying `.bashrc`/`.zshrc` without consent is invasive. nvm does this, but it's controversial | Print PATH export instructions in success banner. Let users choose |
| **Auto-detect leader vs node** | Simpler startup, no flag needed | **Ambiguity** — a machine could be both or neither. Heuristics are fragile | Require explicit `--leader` / `--node` flag. Machine identity is a deployment decision |
| **Install system-wide by default** | More "professional" feel | **Requires sudo** — creates permission friction for curl-pipe-bash. FHS recommends `/opt` for add-on packages but requires root | Default to `~/.local/opt/` (user-writable). Support `MESH_STATUS_HOME=/opt` override for sysadmins |
| **Package manager integration** | dpkg/rpm/brew for production | **Scope creep** — substantial work for each platform. curl-pipe-bash is intentionally distribution-agnostic | Provide install.sh as primary. Document manual steps for packagers. Defer official packages |
| **Prompt for config during install** | "Set it and forget it" | **Pipe mode has no stdin** — `curl ... | bash` literally cannot prompt. Non-interactive mode would still break | Config file + env vars. Print "edit /path/to/config" in success banner |

## Feature Dependencies

```
install.sh
    ├──requires──> git (prerequisite)
    ├──requires──> uv (prerequisite)
    ├──requires──> GitHub repository URL (hardcoded or env overridable)
    │
    ├────enhances──> Version pinning (MESH_STATUS_VERSION env var or tag-based clone)
    │
    └────enhances──> Pre-built frontend (ship dist/ in repo or GitHub release artifact)
                        │
                        └──alternative──> Node.js + npm for building frontend (if no pre-built)
                                                └──requires──> node/npm installed

start.sh
    ├──requires──> install.sh has completed (start.sh lives in install dir)
    │
    ├────enhances──> PID file management (/var/run/mesh-status/ or INSTALL_DIR/var/)
    │
    ├────enhances──> Signal trapping (SIGTERM → graceful shutdown, SIGINT → stop)
    │
    ├────enhances──> Log rotation awareness (separate stdout/stderr logs)
    │
    └────enhances──> Health check (verify /livez responds after start)

Config bootstrapping
    ├──requires──> INSTALL_DIR is writable (to create config file)
    │
    ├────enhances──> Environment variable override (all config values overridable via env)
    │
    └────conflicts──> Interactive prompts (pipe mode has no stdin)
                         │
                         └──solution──> bash -c "$(curl ...)" style OR config file only

CI testing
    └──requires──> Docker available
        └──requires──> install.sh works without tty/stdin
```

### Dependency Notes

- **Version pinning enhances install.sh:** Without it, install.sh always clones HEAD (main branch). Version pinning allows reproducible installs for production.
- **Pre-built frontend vs Node.js build:** Two alternative paths. Pre-built is simpler for the install script (just copy `dist/`) but requires maintainers to commit build artifacts or attach to releases. Building during install requires user to have Node.js installed.
- **PID file management enhances start.sh:** Without PID file, `start.sh` cannot track the process for stop/restart/status operations. Required for proper daemon management.
- **Interactive config conflicts with pipe mode:** This is the fundamental gotcha of curl-pipe-bash. Design config bootstrapping to work WITHOUT stdin (env vars + config file generation with defaults).
- **CI testing requires all non-interactive features:** The Docker-based test must run install.sh with `-y` and pass all config via env vars/flags.

## MVP Definition

### Launch With (v0.8)

Minimum viable install experience — what's needed for INST-01 through INST-04.

- [x] **Prerequisite checks** (uv, git) — bail early with actionable messages
- [x] **Git clone to install dir** — `git clone --depth 1 --branch v0.8.0` with version pinning support
- [x] **`uv sync`** — install Python dependencies
- [x] **Frontend build** — `npm ci && npm run build` (or use pre-built `dist/`)
- [x] **Config file bootstrap** — generate default `.env` config in install dir
- [x] **`start.sh --leader`** — start the leader with hypercorn, PID tracking, log to file
- [x] **`start.sh --node`** — start the node agent with proper args, PID tracking, log to file
- [x] **`start.sh --help`** — print usage for all flags
- [x] **`-y` / `--yes` flag** — skip all confirmations, use defaults
- [x] **`--version` flag** — print installed version
- [x] **Idempotent reinstall** — running `install.sh` again updates in-place via `git pull`
- [x] **Success banner** — print install location, start commands, dashboard URL
- [x] **Uninstall** — `start.sh --uninstall` removes files, prints cleanup instructions
- [x] **Signal handling** — SIGTERM/SIGINT trap for graceful shutdown of started processes
- [x] **Default install to `~/.local/opt/mesh-status/`** with `MESH_STATUS_HOME` override
- [x] **Docker CI test** — verify full install flow in `ubuntu:24.04` container

### Add After Validation (v0.8.x)

Features to add once core install is working.

- [ ] **Systemd service unit generation** — `install.sh --with-systemd` that templates and installs service files
- [ ] **Health check after start** — `start.sh` polls `/livez` before reporting success
- [ ] **Offline detection** — check GitHub reachability before attempting clone
- [ ] **Pre-built dist archive** — GitHub release contains `frontend-dist.tar.gz` to skip Node.js build
- [ ] **Mutual TLS support skeleton** — config stubs for future mTLS between nodes

### Future Consideration (v0.9+)

Features to defer until the install flow is proven.

- [ ] **Official apt/homebrew/brew packages** — distribution-specific packaging
- [ ] **Docker-based install verification in CI** — expand to test uninstall, upgrade paths, multiple OS distros
- [ ] **Auto-update mechanism** — `start.sh` periodically checks for new version and prompts
- [ ] **Install telemetry** — opt-in anonymous usage stats (controversial, handle carefully)
- [ ] **Windows support** — PowerShell installer for Windows nodes (separate scope)
- [ ] **Container-native install** — `docker run mesh-status` instead of bare-metal install

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Prerequisite checks | HIGH | LOW (10 LOC) | P1 |
| Git clone + version pin | HIGH | LOW (15 LOC) | P1 |
| uv sync deps | HIGH | LOW (5 LOC) | P1 |
| Frontend build | HIGH | MEDIUM (npm may not be installed; need fallback or doc) | P1 |
| Config file bootstrap | HIGH | MEDIUM (generate .env with comments) | P1 |
| start.sh --leader | HIGH | MEDIUM (~50 LOC for PID mgmt, signals, logging) | P1 |
| start.sh --node | HIGH | MEDIUM (~50 LOC, shares infra with leader) | P1 |
| -y / --yes flag | HIGH | LOW (10 LOC) | P1 |
| --help flag | MEDIUM | LOW (5 LOC) | P1 |
| Success banner | MEDIUM | LOW (5 LOC) | P1 |
| Idempotent reinstall | HIGH | MEDIUM (detect existing clone, git pull) | P1 |
| Uninstall | MEDIUM | LOW (rm -rf + print instructions) | P1 |
| Signal handling in start.sh | MEDIUM | MEDIUM (trap + graceful shutdown) | P1 |
| Docker CI test | HIGH | HIGH (full Dockerfile + compose for test) | P1 |
| --version flag | MEDIUM | LOW (read from pyproject.toml or git tag) | P1 |
| Offline detection | LOW | LOW (curl -I check before clone) | P2 |
| Health check after start | MEDIUM | MEDIUM (poll endpoint with timeout) | P2 |
| Systemd service generation | MEDIUM | HIGH (template writing, enable/disable logic) | P2 |
| Pre-built frontend dist | HIGH | MEDIUM (CI workflow to attach to release) | P2 |
| Package manager support | MEDIUM | VERY HIGH | P3 |
| Auto-update | LOW | HIGH (background check, user prompting) | P3 |
| Windows support | LOW | VERY HIGH | P3 |

**Priority key:**
- P1: Must have for v0.8
- P2: Should have, add in v0.8.x
- P3: Future consideration

## Competitor Feature Analysis

Comparing against well-known install scripts for similar tools:

| Feature | rustup-init | nvm install.sh | pyenv-installer | mesh-status (planned) |
|---------|-------------|----------------|-----------------|----------------------|
| Shell | sh (POSIX) | bash only | bash | sh (POSIX subset) |
| Prerequisite checks | `need_cmd` for uname, mktemp, etc. | `nvm_has` for git/curl/wget | `command -v git` | `command -v uv`, `command -v git` |
| Idempotent reinstall | Yes (re-downloads installer) | Yes (git pull if .git exists) | No (exits if dir exists) | Yes (git pull in existing repo) |
| Version pinning | `RUSTUP_VERSION` env var | `NVM_INSTALL_VERSION` env var | `PYENV_GIT_TAG` env var | `MESH_STATUS_VERSION` env var + `--version` |
| Non-interactive | `-y` / `--yes` flag | env var `NVM_ENV=testing` | No `-y` flag | `-y` / `--yes` flag |
| Uninstall | Not in installer (separate `rustup self uninstall`) | Not in installer | Manual `rm -rf ~/.pyenv` | `start.sh --uninstall` |
| Install dir | Platform-specific (no override documented in script) | `NVM_DIR` or `~/.nvm` | `PYENV_ROOT` or `~/.pyenv` | `MESH_STATUS_HOME` or `~/.local/opt/mesh-status` |
| Config bootstrapping | None (config managed by rustup binary) | PATH injection into shell rc | PATH instructions printed | `.env` file generation with defaults |
| Success banner | "Rust is installed now. Great!" | "Close and reopen your terminal" | PATH warning | Install path + start commands + dashboard URL |
| Signal handling | N/A (installs, doesn't run) | N/A | N/A | SIGTERM/SIGINT traps for graceful stop |
| PID management | N/A | N/A | N/A | PID file in `$INSTALL_DIR/var/` |
| Logging | Download progress only | Download progress only | Download progress only | stdout/stderr to `$INSTALL_DIR/var/*.log` |

## Sources

### Real-world install scripts analyzed
- [rustup-init.sh](https://raw.githubusercontent.com/rust-lang/rustup/master/rustup-init.sh) — Rust toolchain installer, canonical example of production curl-pipe-bash (HIGH confidence — read full source)
- [nvm install.sh](https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh) — Node Version Manager installer, handles idempotent update via git (HIGH confidence — read full source)
- [pyenv-installer](https://raw.githubusercontent.com/pyenv/pyenv-installer/master/bin/pyenv-installer) — Python version manager installer, multi-plugin git clone pattern (HIGH confidence — read full source)

### Init script / daemon management patterns
- [OpenRC service script guide](https://github.com/martinetd/openrc/blob/bd5cdaafadf997c0ab3c4ad362dbdfd7dc6fd987/service-script-guide.md) — PID files, signal handling, foreground/background daemon management (HIGH confidence — official docs)
- [start-stop-daemon man page](https://man7.org/linux/man-pages/man8/start-stop-daemon.8.html) — PID matching, process management conventions (HIGH confidence — official man page)
- [Init script template](https://github.com/fhd/init-script-template/blob/master/template) — Classic SysV init script pattern with PID file, log handling, stop/start/restart (MEDIUM confidence — community template, pattern verified against OpenRC docs)

### Security best practices
- [Better CLI: Self-executing installation scripts](https://bettercli.org/design/distribution/self-executing-installer/) — curl-pipe-bash design guidance, security considerations (MEDIUM confidence — dedicated guide, aligns with industry practices)
- [Why `curl | bash` is dangerous](https://tferdinand.net/en/why-curl-bash-is-a-dangerous-bad-habit/) — curl-pipe-bash risks, mitigations, server-side detection (MEDIUM confidence — well-researched article, cites real incidents)
- [VNX-BASH-002: curl/wget piped to shell](https://docs.cli.vulnetix.com/docs/sast-rules/vnx-bash-002/) — SAST rule for detecting unsafe pipe patterns (MEDIUM confidence — SAST vendor documentation)
- [Security SE: Is `curl | sudo bash` safe?](https://security.stackexchange.com/questions/213401/is-curl-something-sudo-bash-a-reasonably-safe-installation-method) — Community consensus on pipe-to-shell risks (MEDIUM confidence — curated discussion, multiple expert perspectives)

### FHS / Directory conventions
- [Filesystem Hierarchy Standard 3.0 — /opt](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch03s13.html) — Add-on application package directory standard (HIGH confidence — official FHS)
- [Filesystem Hierarchy Standard 3.0 — /usr/local](https://refspecs.linuxfoundation.org/FHS_3.0/fhs/ch04s09.html) — Locally installed software hierarchy (HIGH confidence — official FHS)
- [XDG Base Directory Specification / file-hierarchy](https://freedesktop.org/software/systemd/man/latest/file-hierarchy.html) — User-specific install paths under `~/.local/` (HIGH confidence — freedesktop.org standard)
- [Unix SE: ~/.local/bin vs /usr/local vs /opt](https://unix.stackexchange.com/questions/36871/where-should-a-local-user-executable-be-placed-under-home) — Community guidance on install directory choice (MEDIUM confidence — community knowledge, verified against FHS)

### Additional conventions
- [Writing init scripts pattern](https://wiki.alpinelinux.org/wiki/Writing_Init_Scripts) — Alpine Linux init script conventions (HIGH confidence — official wiki)
- [PID file handling reference](https://stackoverflow.com/questions/688343/reference-for-proper-handling-of-pid-file-on-unix) — Atomic PID file creation, O_EXCL, stale PID detection (MEDIUM confidence — community knowledge, references Kerrisk's "The Linux Programming Interface")

---
*Feature research for: mesh-status install & start scripts*
*Researched: 2026-06-20*

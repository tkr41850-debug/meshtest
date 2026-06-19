# Phase 4: GitHub Actions CI/CD - Context

**Gathered:** 2026-06-18
**Status:** Ready for planning
**Mode:** Research + Plan

<domain>
## Phase Boundary

Create a GitHub Actions workflow that builds both Docker images (leader+dashboard, node agent) with multi-arch support and pushes to Docker Hub on push/tag.

</domain>

<decisions>
## Implementation Decisions

### Needs Research
The following need investigation before planning:
1. Docker Hub org/repo setup process
2. GitHub secrets configuration
3. GitHub Actions workflow syntax for multi-arch buildx
4. Image tagging strategy (latest + semver tags)

</decisions>

<code_context>
## Existing Code Insights

- `Dockerfile.leader` — Multi-arch Dockerfile, builds with `docker build -f Dockerfile.leader`
- `Dockerfile.node` — Multi-arch Dockerfile, builds with `docker build -f Dockerfile.node`
- Both use UV install script (works for amd64/arm64)
- Compose tested and verified E2E
- Docker Hub username/repo: needs to be decided (e.g., `meshstatus/mesh-leader`, `meshstatus/mesh-node`)

</code_context>

<specifics>
## Specific Ideas

1. `.github/workflows/docker-publish.yml`
2. Build + push on pushes to main and on version tags
3. Multi-arch via docker buildx
4. Docker Hub login via GH secrets
5. Document setup required per environment

</specifics>

<deferred>
## Deferred Ideas

- Multi-registry push (e.g., GHCR + Docker Hub)
- Private registry auth
</deferred>

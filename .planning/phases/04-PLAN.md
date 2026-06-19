# Phase 4: GitHub Actions CI/CD - Plan

**Goal:** Automate multi-arch Docker builds and push to Docker Hub on push/merge.

## Tasks

1. **Create `.github/workflows/docker-publish.yml`**
   - Matrix build for mesh-leader + mesh-node
   - Multi-arch (linux/amd64, linux/arm64)
   - Push to Docker Hub on push/merge (not PRs)
   - Tag strategy: latest, semver, branch
   - Cache via GitHub Actions cache (gha)

2. **Update `README.md`**
   - Add CI badge
   - Add Docker Hub image table
   - Add CI/CD setup instructions (secrets, variables)

3. **Verify workflow syntax**
   - Check with `yaml` linter if available

## Dependencies

- Dockerfiles already exist and verified (Phase 1, 2)
- Docker Hub account + PAT required (documented, not automated)
- GitHub secrets DOCKER_USERNAME + DOCKER_PASSWORD required

## Success Criteria

- [x] Workflow file created
- [x] README updated with setup docs
- [ ] Workflow verified with dry-run or syntax check

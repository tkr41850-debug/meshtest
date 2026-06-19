---
phase: 03
plan: 1
type: execute
wave: 1
depends_on:
  - 01
  - 02
files_modified:
  - compose.yml
  - README.md
autonomous: true
requirements:
  - DOCK-03
  - DOCK-04
  - DOCK-05
must_haves:
  truths:
    - "`docker compose up -d` starts leader and node containers"
    - "Leader /livez endpoint accessible on host port 58080"
    - "Streamlit dashboard accessible on host port 58581"
    - "Node registers with leader automatically"
    - "Data persists in ./data/ directory on host"
    - "README.md documents Docker-based deployment"
  artifacts:
    - path: "compose.yml"
      provides: "Docker Compose file for local dev/test"
      min_lines: 30
    - path: "README.md"
      provides: "Deployment documentation"
      contains: "docker compose"
  key_links:
    - from: "compose.yml"
      to: "Dockerfile.leader"
      via: "build context"
      pattern: "Dockerfile.leader"
    - from: "compose.yml"
      to: "Dockerfile.node"
      via: "build context"
      pattern: "Dockerfile.node"
---

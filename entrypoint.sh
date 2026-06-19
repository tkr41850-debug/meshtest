#!/bin/sh

set -e

LEADER_HOST="${LEADER_HOST:-0.0.0.0}"
LEADER_URL="${LEADER_URL:-http://0.0.0.0:58080}"
LEADER_PORT="${LEADER_URL##*:}"
LEADER_PORT="${LEADER_PORT%%/*}"
case "$LEADER_PORT" in
    ''|*[!0-9]*) LEADER_PORT=58080 ;;
esac
DATA_DIR="${DATA_DIR:-/app/data}"

export LEADER_URL

mkdir -p "$DATA_DIR"

echo "Starting Hypercorn on ${LEADER_HOST}:${LEADER_PORT}..."
exec hypercorn mesh_status.leader:app --bind "${LEADER_HOST}:${LEADER_PORT}"

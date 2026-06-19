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
hypercorn mesh_status.leader:app --bind "${LEADER_HOST}:${LEADER_PORT}" &
HC_PID=$!

for i in $(seq 1 10); do
    if ! kill -0 "$HC_PID" 2>/dev/null; then
        echo "Warning: Hypercorn failed to start — continuing with Streamlit only"
        break
    fi
    if curl -sf "http://${LEADER_HOST}:${LEADER_PORT}/livez" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

echo "Starting Streamlit on port 58581..."
streamlit run mesh_status/dashboard.py \
    --server.port 58581 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --server.runOnSave false &
ST_PID=$!

cleanup() {
    echo "Shutting down..."
    kill "$HC_PID" "$ST_PID" 2>/dev/null
    exit 0
}
trap cleanup TERM INT

while true; do
    if ! kill -0 "$HC_PID" 2>/dev/null || ! kill -0 "$ST_PID" 2>/dev/null; then
        break
    fi
    wait 2>/dev/null
done

kill "$HC_PID" "$ST_PID" 2>/dev/null
wait 2>/dev/null
exit $?

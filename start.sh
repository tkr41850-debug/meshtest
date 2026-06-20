#!/usr/bin/env bash

set -e

INSTALL_DIR="$(cd "$(dirname "$(readlink -f "$0")")" && pwd)"

load_env() {
    if [ -f "$INSTALL_DIR/.env" ]; then
        set -a
        . "$INSTALL_DIR/.env"
        set +a
    fi
}

usage() {
    cat <<EOF
start.sh — mesh-status runner

Usage: start.sh [options]

Options:
  --leader              Start the leader process (Hypercorn)
  --node                Start the node agent
  --leader-url <url>    Leader URL override (default: http://0.0.0.0:58080)
  --node-ip <ip>        Node IP override
  --leader-ip <ip>      Leader IP for node registration
  --configure           Force config wizard
  --uninstall           Remove the install directory
  --version             Show installed version
  --help                Show this help message
EOF
    exit 0
}

ROLE=""
LEADER_URL=""
NODE_IP=""
LEADER_IP=""
CONFIGURE=0
UNINSTALL=0
SHOW_VERSION=0

while [ $# -gt 0 ]; do
    case "$1" in
        --leader) ROLE="leader" ;;
        --node) ROLE="node" ;;
        --leader-url) LEADER_URL="$2"; shift ;;
        --node-ip) NODE_IP="$2"; shift ;;
        --leader-ip) LEADER_IP="$2"; shift ;;
        --configure) CONFIGURE=1 ;;
        --uninstall) UNINSTALL=1 ;;
        --version) SHOW_VERSION=1 ;;
        --help) usage ;;
        *) echo "Unknown option: $1"; usage ;;
    esac
    shift
done

if [ "$SHOW_VERSION" = 1 ]; then
    if [ -f "$INSTALL_DIR/.mesh-status.install" ]; then
        cat "$INSTALL_DIR/.mesh-status.install"
    else
        echo "unknown"
    fi
    exit 0
fi

if [ "$UNINSTALL" = 1 ]; then
    echo "Removing $INSTALL_DIR..."
    rm -rf "$INSTALL_DIR"
    echo "Removed $INSTALL_DIR"
    echo ""
    echo "To clean up your PATH, remove this line from your shell rc file:"
    echo "  export PATH=\"\$PATH:$INSTALL_DIR\""
    exit 0
fi

load_env

HAS_CLI_FLAGS=0
[ -n "$LEADER_URL" ] && HAS_CLI_FLAGS=1
[ -n "$NODE_IP" ] && HAS_CLI_FLAGS=1
[ -n "$LEADER_IP" ] && HAS_CLI_FLAGS=1
[ "$CONFIGURE" = 1 ] && HAS_CLI_FLAGS=0

if [ "$ROLE" = "" ]; then
    if [ "$HAS_CLI_FLAGS" = 0 ] && [ -t 0 ]; then
        echo "Select role:"
        echo "  1) Leader"
        echo "  2) Node"
        printf "Choice [1]: "
        read -r ROLE_CHOICE
        case "$ROLE_CHOICE" in
            2|node) ROLE="node" ;;
            *) ROLE="leader" ;;
        esac
    else
        echo "Error: specify --leader or --node"
        exit 1
    fi
fi

if [ "$ROLE" = "leader" ]; then
    if [ "$HAS_CLI_FLAGS" = 0 ] && [ -t 0 ]; then
        printf "Leader host [${LEADER_HOST:-0.0.0.0}]: "
        read -r INPUT
        [ -n "$INPUT" ] && LEADER_HOST="$INPUT"
        printf "Leader port [${LEADER_PORT:-58080}]: "
        read -r INPUT
        [ -n "$INPUT" ] && LEADER_PORT="$INPUT"
    fi
fi

if [ "$ROLE" = "node" ]; then
    if [ "$HAS_CLI_FLAGS" = 0 ] && [ -t 0 ]; then
        printf "Leader URL [${LEADER_URL:-http://0.0.0.0:58080}]: "
        read -r INPUT
        [ -n "$INPUT" ] && LEADER_URL="$INPUT"
        printf "Node IP: "
        read -r NODE_IP
        printf "Leader IP [${LEADER_IP:-}]: "
        read -r INPUT
        [ -n "$INPUT" ] && LEADER_IP="$INPUT"
    fi
fi

if [ "$ROLE" = "leader" ]; then
    LOG_FILE="$INSTALL_DIR/var/leader.log"
    PID_FILE="$INSTALL_DIR/var/leader.pid"
    mkdir -p "$INSTALL_DIR/var"
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Leader is already running (PID $(cat "$PID_FILE"))"
        exit 1
    fi
    rm -f "$PID_FILE"
    echo "Starting leader..."
    exec >> "$LOG_FILE" 2>&1
    echo $$ > "$PID_FILE"
    trap 'rm -f "$PID_FILE"; exit' SIGTERM SIGINT
    exec uv run hypercorn mesh_status.leader:app --bind "${LEADER_HOST:-0.0.0.0}:${LEADER_PORT:-58080}"
fi

if [ "$ROLE" = "node" ]; then
    LOG_FILE="$INSTALL_DIR/var/node.log"
    PID_FILE="$INSTALL_DIR/var/node.pid"
    mkdir -p "$INSTALL_DIR/var"
    if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
        echo "Node is already running (PID $(cat "$PID_FILE"))"
        exit 1
    fi
    rm -f "$PID_FILE"
    echo "Starting node..."
    exec >> "$LOG_FILE" 2>&1
    echo $$ > "$PID_FILE"
    trap 'rm -f "$PID_FILE"; exit' SIGTERM SIGINT
    NODE_ARGS=""
    [ -n "$LEADER_URL" ] && NODE_ARGS="$NODE_ARGS --leader-url $LEADER_URL"
    [ -n "$NODE_IP" ] && NODE_ARGS="$NODE_ARGS --node-ip $NODE_IP"
    [ -n "$LEADER_IP" ] && NODE_ARGS="$NODE_ARGS --leader-ip $LEADER_IP"
    exec uv run python node.py $NODE_ARGS
fi

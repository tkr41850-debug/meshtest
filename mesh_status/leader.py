import asyncio
import json
import logging
import sys
import time
from typing import Optional

import httpx
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, request, jsonify
from quart_cors import cors

from mesh_status import config
from mesh_status.models import CheckResult, NodeInfo, NodeRegistration, SubmitPayload

app = Quart(__name__)
cors(app, allow_origin="*")

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    stream=sys.stderr,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("mesh-status")

_registry: dict[str, NodeInfo] = {}
_registry_lock = asyncio.Lock()
_results: dict[str, list[dict]] = {}
_peers_by_node: dict[str, list[str]] = {}


@app.route("/livez", methods=["GET"])
async def livez():
    return {"status": "alive"}, 200


@app.route("/readyz", methods=["GET"])
async def readyz():
    return {"status": "ready"}, 200


@app.route("/register", methods=["POST"])
async def register():
    data = await request.get_json()
    if not data or "node_ip" not in data:
        return {"error": "Missing node_ip", "status": 400}, 400

    node_ip = data["node_ip"]
    hostname = data.get("hostname")

    async with _registry_lock:
        if node_ip in _registry:
            _registry[node_ip].last_seen = time.time()
            logger.info("Node re-registered: %s", node_ip)
        else:
            _registry[node_ip] = NodeInfo(
                node_ip=node_ip, hostname=hostname, last_seen=time.time()
            )
            logger.info("Node registered: %s", node_ip)

    await _push_peer_list_to_all()

    peers = list(_registry.keys())
    return {"status": "registered", "peers": peers}, 200


@app.route("/node-list", methods=["GET"])
async def node_list():
    async with _registry_lock:
        nodes = list(_registry.keys())
    return {"nodes": nodes, "count": len(nodes)}, 200


@app.route("/submit", methods=["POST"])
async def submit_results():
    data = await request.get_json()
    if not data:
        return {"error": "Invalid payload: empty body", "status": 400}, 400

    node_ip = data.get("node_ip")
    checks = data.get("checks")
    timestamp = data.get("timestamp")

    if not isinstance(node_ip, str):
        return {"error": "Invalid payload: node_ip must be a string", "status": 400}, 400
    if not isinstance(checks, list) or len(checks) == 0:
        return {"error": "Invalid payload: checks must be a non-empty array", "status": 400}, 400
    if not isinstance(timestamp, (int, float)):
        return {"error": "Invalid payload: timestamp must be a number", "status": 400}, 400

    _results[node_ip] = checks
    logger.info("Results submitted from %s: %d checks", node_ip, len(checks))
    return {"status": "accepted", "count": len(checks)}, 202


@app.route("/updateConfig", methods=["POST"])
async def update_config():
    data = await request.get_json()
    if not data:
        return {"error": "Empty body", "status": 400}, 400

    if "check_interval" in data:
        config.CHECK_INTERVAL = int(data["check_interval"])
    if "buffer_size" in data:
        config.BUFFER_SIZE = int(data["buffer_size"])

    await _push_config_to_all()
    return {
        "status": "config_updated",
        "config": {"check_interval": config.CHECK_INTERVAL, "buffer_size": config.BUFFER_SIZE},
    }, 200


async def _notify_node(node_ip: str, peers: list[str]):
    url = f"http://{node_ip}:{config.LEADER_PORT}/update-peers"
    try:
        async with httpx.AsyncClient(timeout=config.PEER_PUSH_TIMEOUT) as client:
            resp = await client.post(url, json={
                "peers": peers,
                "check_interval": config.CHECK_INTERVAL,
                "buffer_size": config.BUFFER_SIZE,
            })
            resp.raise_for_status()
            logger.debug("Peer notification sent to %s", node_ip)
    except Exception as e:
        logger.warning("Failed to notify node %s: %s", node_ip, e)


async def _push_peer_list_to_all():
    async with _registry_lock:
        all_peers = list(_registry.keys())
        tasks = [_notify_node(ip, all_peers) for ip in all_peers]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def _push_config_to_all():
    async with _registry_lock:
        all_peers = list(_registry.keys())
        tasks = []
        for ip in all_peers:
            tasks.append(_notify_node(ip, list(_registry.keys())))
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def main():
    hypercorn_config = Config()
    hypercorn_config.bind = [f"0.0.0.0:{config.LEADER_PORT}"]
    logger.info("Starting mesh-status leader on port %d", config.LEADER_PORT)
    asyncio.run(serve(app, hypercorn_config))

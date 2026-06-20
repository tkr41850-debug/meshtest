import asyncio
import logging
import os
import sys
import time
from datetime import datetime, timedelta, date
from pathlib import Path
from urllib.parse import urlparse

import httpx
from hypercorn.asyncio import serve
from hypercorn.config import Config
from quart import Quart, request, jsonify, send_from_directory
from quart_cors import cors

from mesh_status import config
from mesh_status.models import NodeInfo
from mesh_status import persistence
from mesh_status import status as status_module

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


def _leader_port() -> int:
    url = os.environ.get("LEADER_URL", f"http://0.0.0.0:{config.DEFAULT_PORT}")
    parsed = urlparse(url)
    return parsed.port or config.DEFAULT_PORT


@app.before_serving
async def startup():
    asyncio.create_task(persistence.flush_loop())
    logger.info("Background flush task started")


_dist_dir = Path(__file__).resolve().parent.parent / "dist"


@app.route("/")
async def index():
    return await send_from_directory(str(_dist_dir), "index.html")


@app.route("/assets/<path:filename>")
async def assets(filename):
    return await send_from_directory(str(_dist_dir / "assets"), filename)


@app.route("/livez", methods=["GET"])
async def livez():
    return {"status": "alive"}, 200


@app.route("/readyz", methods=["GET"])
async def readyz():
    return {"status": "ready"}, 200


@app.route("/healthz", methods=["GET"])
async def healthz():
    return {"status": "alive"}, 200


@app.route("/register", methods=["POST"])
async def register():
    data = await request.get_json()
    if not data or "node_ip" not in data:
        return {"error": "Missing node_ip", "status": 400}, 400

    node_ip = data["node_ip"]
    hostname = data.get("hostname")
    listen_port = data.get("listen_port", config.DEFAULT_PORT)
    node_url = data.get("node_url")

    async with _registry_lock:
        if node_ip in _registry:
            _registry[node_ip].last_seen = time.time()
            _registry[node_ip].listen_port = listen_port
            _registry[node_ip].node_url = node_url
            logger.info("Node re-registered: %s", node_ip)
        else:
            _registry[node_ip] = NodeInfo(
                node_ip=node_ip, hostname=hostname, last_seen=time.time(),
                listen_port=listen_port, node_url=node_url,
            )
            logger.info("Node registered: %s", node_ip)

    await _push_peer_list_to_all()

    peers = _peer_dicts()
    return {"status": "registered", "peers": peers}, 200


@app.route("/node-list", methods=["GET"])
async def node_list():
    async with _registry_lock:
        nodes = _peer_dicts()
    return {"nodes": nodes, "count": len(nodes)}, 200


@app.route("/submit", methods=["POST"])
async def submit_results():
    data = await request.get_json()
    if not data:
        return {"error": "Invalid payload: empty body", "status": 400}, 400

    node_ip = data.get("node_ip")
    checks = data.get("checks")
    timestamp = data.get("timestamp")
    node_url = data.get("node_url", "")

    if not isinstance(node_ip, str):
        return {"error": "Invalid payload: node_ip must be a string", "status": 400}, 400
    if not isinstance(checks, list) or len(checks) == 0:
        return {"error": "Invalid payload: checks must be a non-empty array", "status": 400}, 400
    if not isinstance(timestamp, (int, float)):
        return {"error": "Invalid payload: timestamp must be a number", "status": 400}, 400

    if node_ip in _results:
        _results[node_ip].extend(checks)
    else:
        _results[node_ip] = list(checks)
    logger.info("Results submitted from %s: %d checks", node_ip, len(checks))

    async with _registry_lock:
        if node_ip not in _registry and node_url:
            parsed = urlparse(node_url)
            listen_port = parsed.port or config.DEFAULT_PORT
            _registry[node_ip] = NodeInfo(
                node_ip=node_ip, listen_port=listen_port, node_url=node_url,
                last_seen=time.time(),
            )
            logger.info("Auto-registered node %s from submit", node_ip)
            asyncio.create_task(_push_peer_list_to_all())

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


@app.route("/data", methods=["GET"])
async def get_data():
    window = request.args.get("window", "")
    if window == "30m":
        cutoff = time.time() - 1800
        checks = []
        for node_ip, node_results in _results.items():
            for r in node_results:
                if r.get("timestamp", 0) >= cutoff:
                    check = dict(r)
                    check["node_ip"] = node_ip
                    checks.append(check)
        statuses = []
        now = time.time()
        for src_ip in list(_registry.keys()):
            for dst_ip in list(_registry.keys()):
                if src_ip != dst_ip:
                    s = status_module.calculate_status(src_ip, dst_ip, _results, _registry, now)
                    statuses.append(s)
        return {"window": "30m", "checks": checks, "statuses": statuses, "timestamp": now}, 200

    elif window == "30d":
        now = time.time()
        start = (datetime.now() - timedelta(days=30)).date()
        end = datetime.now().date()
        raw = persistence._read_results(start, end)
        # Infer node_ip for disk records with empty node_ip (stored before Phase 12 fix)
        target_to_source: dict[str, str] = {}
        for src_ip, src_results in _results.items():
            for sr in src_results:
                tgt = sr.get("target_ip", "")
                if tgt and tgt not in target_to_source:
                    target_to_source[tgt] = src_ip
        for r in raw:
            if not r.get("node_ip"):
                r["node_ip"] = target_to_source.get(r.get("target_ip", ""), "")
        # Include in-memory data that hasn't been flushed yet
        for node_ip, node_results in list(_results.items()):
            for r in node_results:
                check = dict(r)
                check["node_ip"] = node_ip
                raw.append(check)
        by_day: dict[str, dict] = {}
        for r in raw:
            ts = r.get("timestamp", 0)
            day = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            if day not in by_day:
                by_day[day] = {}
            key = (r.get("node_ip", ""), r.get("target_ip", ""))
            if key not in by_day[day]:
                by_day[day][key] = {"total": 0, "ping_ok": 0, "http_ok": 0}
            by_day[day][key]["total"] += 1
            if r.get("ping_ok"):
                by_day[day][key]["ping_ok"] += 1
            if r.get("http_ok"):
                by_day[day][key]["http_ok"] += 1

        days_list = []
        for day_str in sorted(by_day.keys()):
            connections = []
            for (src, dst), stats in by_day[day_str].items():
                connections.append({
                    "node_ip": src,
                    "target_ip": dst,
                    "total_checks": stats["total"],
                    "ping_uptime_pct": round(stats["ping_ok"] / stats["total"] * 100, 1),
                    "http_uptime_pct": round(stats["http_ok"] / stats["total"] * 100, 1),
                })
            days_list.append({"date": day_str, "connections": connections})
        return {"window": "30d", "days": days_list, "timestamp": now}, 200

    else:
        return {"error": "Invalid or missing window parameter. Use ?window=30m or ?window=30d", "status": 400}, 400


def _node_peer_push_url(node: NodeInfo) -> str:
    if node.node_url:
        return f"{node.node_url.rstrip('/')}/update-peers"
    return f"http://{node.node_ip}:{node.listen_port}/update-peers"


def _peer_dicts() -> list[dict]:
    return [
        {"ip": ip, "port": info.listen_port}
        for ip, info in _registry.items()
    ]


async def _notify_node(node_ip: str, peers: list[dict]):
    node = _registry.get(node_ip)
    if not node:
        return
    url = _node_peer_push_url(node)
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
        all_ips = list(_registry.keys())
        peer_dicts = _peer_dicts()
        tasks = [_notify_node(ip, peer_dicts) for ip in all_ips]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def _push_config_to_all():
    async with _registry_lock:
        all_ips = list(_registry.keys())
        peer_dicts = _peer_dicts()
        tasks = [_notify_node(ip, peer_dicts) for ip in all_ips]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def main():
    port = _leader_port()
    hypercorn_config = Config()
    hypercorn_config.bind = [f"0.0.0.0:{port}"]
    logger.info("Starting mesh-status leader on port %d", port)
    asyncio.run(serve(app, hypercorn_config))

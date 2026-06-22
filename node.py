#!/usr/bin/env python3
"""Node agent for mesh-status — runs periodic connectivity checks."""

import argparse
import asyncio
import logging
import os
import re
import socket
import sys
import time
from collections import deque
from urllib.parse import urlparse

import httpx

from mesh_status import config
from aiohttp import web

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    stream=sys.stderr,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("mesh-status-node")


def parse_args():
    parser = argparse.ArgumentParser(description="mesh-status node agent")
    parser.add_argument(
        "--leader-url",
        "-l",
        default=os.environ.get("LEADER_URL", f"http://localhost:{config.DEFAULT_PORT}"),
        help="Leader URL (e.g. http://leader:58080)",
    )
    parser.add_argument(
        "--node-url",
        "-n",
        default=os.environ.get("NODE_URL", ""),
        help="This node's URL (e.g. http://node1:58081)",
    )
    return parser.parse_args()


def get_own_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except Exception:
        return socket.gethostbyname(socket.gethostname())


def _parse_node_url(url: str) -> tuple[str, int]:
    if not url:
        return get_own_ip(), config.DEFAULT_PORT
    parsed = urlparse(url)
    hostname = parsed.hostname or get_own_ip()
    port = parsed.port or config.DEFAULT_PORT
    return hostname, port


async def check_node(target_ip: str, port: int = config.DEFAULT_PORT, timeout: float = 5.0) -> dict:
    timestamp = time.time()
    ping_ok = False
    ping_latency_ms = None
    http_ok = False
    http_latency_ms = None
    http_status = None

    proc = await asyncio.create_subprocess_exec(
        "ping",
        "-c",
        "1",
        "-W",
        str(int(timeout)),
        target_ip,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 0.5)
        if proc.returncode == 0:
            ping_ok = True
            match = re.search(r"time=(\d+\.?\d*)\s*ms", stdout.decode(errors="replace"))
            if match:
                ping_latency_ms = float(match.group(1))
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

    try:
        http_start = time.time()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"http://{target_ip}:{port}/healthz")
            http_latency_ms = (time.time() - http_start) * 1000
            http_ok = resp.is_success
            http_status = resp.status_code
    except Exception as e:
        logger.debug("HTTP check to %s:%d failed: %s", target_ip, port, e)

    return {
        "target_ip": target_ip,
        "ping_ok": ping_ok,
        "ping_latency_ms": ping_latency_ms,
        "http_ok": http_ok,
        "http_status": http_status,
        "http_latency_ms": http_latency_ms,
        "timestamp": timestamp,
    }


async def run_check_cycle(
    semaphore: asyncio.Semaphore, peers: list[dict], timeout: float = 5.0
) -> list[dict]:
    async def limited_check(peer: dict):
        async with semaphore:
            return await check_node(peer["ip"], peer.get("port", config.DEFAULT_PORT), timeout)

    results = await asyncio.gather(*[limited_check(p) for p in peers], return_exceptions=True)
    return [r for r in results if isinstance(r, dict)]


async def submit_results(
    results: list[dict], node_ip: str, leader_url: str, node_url: str = ""
) -> bool:
    url = f"{leader_url.rstrip('/')}/submit"
    payload = {
        "node_ip": node_ip,
        "node_url": node_url,
        "checks": results,
        "timestamp": time.time(),
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload)
            if resp.is_success:
                return True
            logger.warning("Submit failed: HTTP %d", resp.status_code)
            return False
    except Exception as e:
        logger.warning("Submit failed: %s", e)
        return False


async def handle_healthz(request: web.Request) -> web.Response:
    return web.json_response({"status": "alive"})


async def handle_update_peers(request: web.Request) -> web.Response:
    data = await request.json()
    app = request.app
    app["state"]["peers"] = data.get("peers", app["state"]["peers"])
    if "check_interval" in data:
        app["state"]["interval"] = int(data["check_interval"])
    if "buffer_size" in data:
        app["state"]["buffer_size"] = int(data["buffer_size"])
    logger.info(
        "Updated peers via push: %d peers, interval=%s, buffer=%s",
        len(app["state"]["peers"]),
        app["state"]["interval"],
        app["state"]["buffer_size"],
    )
    return web.json_response({"status": "ok"})


async def start_http_server(state: dict, host: str = "0.0.0.0", port: int = 0) -> web.AppRunner:
    app = web.Application()
    app["state"] = state
    app.router.add_get("/healthz", handle_healthz)
    app.router.add_post("/update-peers", handle_update_peers)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info("Node HTTP server listening on %s:%d", host, port)
    return runner


async def run():
    args = parse_args()

    leader_url = args.leader_url
    node_ip, listen_port = _parse_node_url(args.node_url)
    node_url = args.node_url

    shared_state = {
        "peers": [],
        "interval": config.CHECK_INTERVAL,
        "buffer_size": config.BUFFER_SIZE,
    }
    http_runner = await start_http_server(shared_state, port=listen_port)
    buffer_size = shared_state["buffer_size"]
    result_buffer: deque[list[dict]] = deque(maxlen=buffer_size)
    semaphore = asyncio.Semaphore(10)

    logger.info("Registering with leader at %s as %s", leader_url, node_ip)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"{leader_url.rstrip('/')}/register",
            json={"node_ip": node_ip, "listen_port": listen_port, "node_url": node_url},
        )
        if not resp.is_success:
            logger.error("Registration failed: %s", resp.text)
            sys.exit(1)
        data = resp.json()
        if "peers" in data and isinstance(data["peers"], list):
            shared_state["peers"] = data["peers"]
        logger.info("Registered. Peers: %s", shared_state["peers"])

    try:
        while True:
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(f"{leader_url.rstrip('/')}/node-list")
                    if resp.is_success:
                        shared_state["peers"] = resp.json().get("nodes", [])

                logger.debug("Check cycle: %d peers", len(shared_state["peers"]))
                results = await run_check_cycle(semaphore, shared_state["peers"])

                combined = list(result_buffer)
                combined.append(results)

                all_checks: list[dict] = []
                for batch in combined:
                    all_checks.extend(batch)

                ok = await submit_results(all_checks, node_ip, leader_url, node_url)
                if ok:
                    result_buffer.clear()
                    if len(combined) > 1:
                        logger.info("Buffered data submitted successfully")
                else:
                    result_buffer.append(results)
                    logger.warning("Buffer size: %d cycles", len(result_buffer))

            except Exception as e:
                logger.error("Check cycle error: %s", e)

            await asyncio.sleep(shared_state["interval"])
    finally:
        try:
            await http_runner.cleanup()
        except Exception:
            pass


if __name__ == "__main__":
    asyncio.run(run())

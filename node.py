#!/usr/bin/env python3
"""Node agent for mesh-status — runs periodic connectivity checks."""

import argparse
import asyncio
import json
import logging
import re
import socket
import sys
import time
from collections import deque

import httpx

from mesh_status import config

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    stream=sys.stderr,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("mesh-status-node")


def parse_args():
    parser = argparse.ArgumentParser(description="mesh-status node agent")
    parser.add_argument("--leader-ip", "-l", help="Leader server IP address")
    parser.add_argument("--node-ip", "-n", help="This node's IP address")
    parser.add_argument("--port", "-p", type=int, default=config.LEADER_PORT, help="Leader port")
    return parser.parse_args()


def get_own_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            return s.getsockname()[0]
    except Exception:
        return socket.gethostbyname(socket.gethostname())


async def check_node(
    target_ip: str, timeout: float = 5.0
) -> dict:
    timestamp = time.time()
    ping_ok = False
    ping_latency_ms = None
    http_ok = False
    http_latency_ms = None
    http_status = None

    proc = await asyncio.create_subprocess_exec(
        "ping", "-c", "1", "-W", str(int(timeout)),
        target_ip,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        await asyncio.wait_for(proc.wait(), timeout=timeout + 0.5)
        stdout, _ = await proc.communicate()
        if proc.returncode == 0:
            ping_ok = True
            match = re.search(r"time=(\d+\.?\d*)\s*ms", stdout.decode())
            if match:
                ping_latency_ms = float(match.group(1))
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()

    try:
        http_start = time.time()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(f"http://{target_ip}:{config.LEADER_PORT}/healthz")
            http_latency_ms = (time.time() - http_start) * 1000
            http_ok = resp.is_success
            http_status = resp.status_code
    except Exception:
        pass

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
    semaphore: asyncio.Semaphore, peers: list[str], timeout: float = 5.0
) -> list[dict]:
    async def limited_check(ip: str):
        async with semaphore:
            return await check_node(ip, timeout)

    results = await asyncio.gather(*[limited_check(ip) for ip in peers], return_exceptions=True)
    return [r for r in results if isinstance(r, dict)]


async def submit_results(
    results: list[dict], node_ip: str, leader_ip: str, port: int
) -> bool:
    url = f"http://{leader_ip}:{port}/submit"
    payload = {"node_ip": node_ip, "checks": results, "timestamp": time.time()}
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


async def run():
    args = parse_args()

    leader_ip = args.leader_ip
    if not leader_ip:
        leader_ip = input("Enter leader IP: ").strip()

    node_ip = args.node_ip or get_own_ip()
    port = args.port
    interval = config.CHECK_INTERVAL
    buffer_size = config.BUFFER_SIZE
    result_buffer: deque[list[dict]] = deque(maxlen=buffer_size)
    semaphore = asyncio.Semaphore(10)

    logger.info("Registering with leader at %s:%d as %s", leader_ip, port, node_ip)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            f"http://{leader_ip}:{port}/register",
            json={"node_ip": node_ip},
        )
        if not resp.is_success:
            logger.error("Registration failed: %s", resp.text)
            sys.exit(1)
        data = resp.json()
        peers = data.get("peers", [])
        logger.info("Registered. Peers: %s", peers)

    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"http://{leader_ip}:{port}/node-list")
                if resp.is_success:
                    peers = resp.json().get("nodes", [])

            logger.debug("Check cycle: %d peers", len(peers))
            results = await run_check_cycle(semaphore, peers)

            combined = list(result_buffer)
            combined.append(results)

            for batch in combined:
                ok = await submit_results(batch, node_ip, leader_ip, port)
                if ok:
                    result_buffer.clear()
                    if len(combined) > 1:
                        logger.info("Buffered data submitted successfully")
                    break
                else:
                    result_buffer.append(batch)
                    logger.warning("Buffer size: %d cycles", len(result_buffer))

        except Exception as e:
            logger.error("Check cycle error: %s", e)

        await asyncio.sleep(interval)


if __name__ == "__main__":
    asyncio.run(run())

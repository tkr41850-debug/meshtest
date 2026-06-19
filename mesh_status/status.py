import time

from mesh_status import config


def calculate_status(
    node_ip: str, target_ip: str,
    results: dict[str, list[dict]],
    registry: dict, now: float = None
) -> dict:
    if now is None:
        now = time.time()
    threshold = max(config.GRACE_PERIOD, 3 * config.CHECK_INTERVAL)

    node_results = results.get(node_ip, [])
    has_results = len(node_results) > 0

    if not has_results:
        return {
            "node_ip": node_ip,
            "target_ip": target_ip,
            "ping_status": "Pending",
            "http_status": "Pending",
            "last_seen": None,
        }

    # Find latest result for this target
    latest = None
    for r in node_results:
        if r.get("target_ip") == target_ip:
            if latest is None or r.get("timestamp", 0) > latest.get("timestamp", 0):
                latest = r

    if latest is None:
        return {
            "node_ip": node_ip,
            "target_ip": target_ip,
            "ping_status": "Pending",
            "http_status": "Pending",
            "last_seen": None,
        }

    last_ts = latest.get("timestamp", 0)
    is_recent = (now - last_ts) <= threshold

    if not is_recent:
        return {
            "node_ip": node_ip,
            "target_ip": target_ip,
            "ping_status": "NotAvailable",
            "http_status": "NotAvailable",
            "last_seen": last_ts,
        }

    # Result exists and is recent — status per check type
    ping_ok = latest.get("ping_ok", False)
    http_ok = latest.get("http_ok", False)

    return {
        "node_ip": node_ip,
        "target_ip": target_ip,
        "ping_status": "OK" if ping_ok else "NotAvailable",
        "http_status": "OK" if http_ok else "NotAvailable",
        "last_seen": last_ts,
    }

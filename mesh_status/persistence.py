import asyncio
import json
import logging
import os
import time
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger("mesh-status-persistence")

DATA_ROOT = Path(os.environ.get("DATA_DIR", "data"))


def _ensure_data_dir(d: date) -> Path:
    path = DATA_ROOT / str(d.year) / f"{d.month:02d}" / f"{d.day:02d}"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _date_path(d: date) -> Path:
    return DATA_ROOT / str(d.year) / f"{d.month:02d}" / f"{d.day:02d}.json"


def _append_results(d: date, results: list[dict]):
    if not results:
        return
    path = _date_path(d)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_suffix(".tmp")
    mode = "a" if path.exists() else "w"
    with open(tmp_path, mode) as f:
        for item in results:
            f.write(json.dumps(item, default=str) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, path)


def _read_results(start_date: date, end_date: date) -> list[dict]:
    results = []
    current = start_date
    while current <= end_date:
        path = _date_path(current)
        if path.exists():
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line:
                        results.append(json.loads(line))
        current += timedelta(days=1)
    results.sort(key=lambda r: r.get("timestamp", 0))
    return results


def _flush_results(results_batch: dict[str, list[dict]]):
    by_date: dict[date, list[dict]] = {}
    for node_ip, checks in results_batch.items():
        for check in checks:
            ts = check.get("timestamp", time.time())
            dt = datetime.fromtimestamp(ts).date()
            stored = dict(check)
            stored["node_ip"] = node_ip
            by_date.setdefault(dt, []).append(stored)
    for d, items in by_date.items():
        _append_results(d, items)
        logger.info("Flushed %d results to %s", len(items), _date_path(d))


async def load_into_memory(
    results_store: dict[str, list[dict]],
    day_aggregates: dict[str, dict],
):
    """Load disk data into in-memory stores on leader startup.

    Data within last 90h → raw results in results_store.
    Data older than 90h → daily aggregates in day_aggregates.
    """
    cutoff_90h = time.time() - 90 * 3600
    start = (datetime.now() - timedelta(days=90)).date()
    end = datetime.now().date()
    raw = _read_results(start, end)

    target_to_source: dict[str, str] = {}
    loaded_raw = 0
    loaded_agg = 0

    for r in raw:
        ts = r.get("timestamp", 0)
        node_ip = r.get("node_ip", "")
        target_ip = r.get("target_ip", "")

        if not node_ip and target_ip:
            node_ip = target_to_source.get(target_ip, "")
        if node_ip and target_ip and node_ip not in target_to_source:
            target_to_source[target_ip] = node_ip

        if ts >= cutoff_90h:
            if node_ip not in results_store:
                results_store[node_ip] = []
            check = {k: v for k, v in r.items() if k != "node_ip"}
            results_store[node_ip].append(check)
            loaded_raw += 1
        else:
            day = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            if day not in day_aggregates:
                day_aggregates[day] = {}
            key = (node_ip, target_ip)
            if key not in day_aggregates[day]:
                day_aggregates[day][key] = {"total": 0, "ping_ok": 0, "http_ok": 0}
            day_aggregates[day][key]["total"] += 1
            if r.get("ping_ok"):
                day_aggregates[day][key]["ping_ok"] += 1
            if r.get("http_ok"):
                day_aggregates[day][key]["http_ok"] += 1
            loaded_agg += 1

    logger.info(
        "Loaded from disk: %d raw results, %d aggregated checks across %d days",
        loaded_raw,
        loaded_agg,
        len(day_aggregates),
    )


async def flush_loop(interval: int = 3600):
    """Background task: flush _results to disk every `interval` seconds.

    After flushing, moves data older than 90h to daily aggregates
    and removes it from _results.
    """
    from mesh_status.leader import _results, _day_aggregates

    while True:
        await asyncio.sleep(interval)
        if _results:
            batch = dict(_results)
            _flush_results(batch)
            cutoff_90h = time.time() - 90 * 3600
            for node_ip in list(_results.keys()):
                recent = []
                for r in _results[node_ip]:
                    ts = r.get("timestamp", 0)
                    if ts >= cutoff_90h:
                        recent.append(r)
                    else:
                        day = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                        if day not in _day_aggregates:
                            _day_aggregates[day] = {}
                        key = (node_ip, r.get("target_ip", ""))
                        if key not in _day_aggregates[day]:
                            _day_aggregates[day][key] = {"total": 0, "ping_ok": 0, "http_ok": 0}
                        _day_aggregates[day][key]["total"] += 1
                        if r.get("ping_ok"):
                            _day_aggregates[day][key]["ping_ok"] += 1
                        if r.get("http_ok"):
                            _day_aggregates[day][key]["http_ok"] += 1
                if recent:
                    _results[node_ip] = recent
                else:
                    del _results[node_ip]
            logger.debug(
                "Flush complete: %d nodes in _results, %d days in _day_aggregates",
                len(_results),
                len(_day_aggregates),
            )

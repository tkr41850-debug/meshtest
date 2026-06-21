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


async def flush_loop(interval: int = 3600):
    """Background task: flush _results to disk every `interval` seconds."""
    from mesh_status.leader import _results

    while True:
        await asyncio.sleep(interval)
        if _results:
            batch = dict(_results)
            _flush_results(batch)
            # Keep last 10 minutes in memory
            cutoff = time.time() - 5400
            for node_ip in list(_results.keys()):
                _results[node_ip] = [
                    r for r in _results[node_ip] if r.get("timestamp", 0) >= cutoff
                ]

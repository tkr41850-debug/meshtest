import json
import time
from datetime import date, datetime, timedelta
from pathlib import Path

from mesh_status import config


# Test that config loads
def test_config_has_defaults():
    assert hasattr(config, "DEFAULT_PORT")


class TestPersistence:
    def test_ensure_data_dir_creates_path(self):
        from mesh_status.persistence import _ensure_data_dir

        d = date(2026, 6, 18)
        path = _ensure_data_dir(d)
        assert path.parent.exists()
        assert path.parent.name == "06"
        assert path.parent.parent.name == "2026"

    def test_append_and_read_results(self):
        from mesh_status.persistence import _append_results, _read_results

        d = date(2026, 6, 18)
        results = [
            {"node_ip": "10.0.0.1", "target_ip": "10.0.0.2", "ping_ok": True, "timestamp": 100.0},
            {"node_ip": "10.0.0.1", "target_ip": "10.0.0.3", "ping_ok": False, "timestamp": 101.0},
        ]
        _append_results(d, results)
        read_back = _read_results(d, d)
        assert len(read_back) == 2
        assert read_back[0]["node_ip"] == "10.0.0.1"
        assert read_back[0]["target_ip"] == "10.0.0.2"

    def test_empty_read_returns_empty_list(self):
        from mesh_status.persistence import _read_results

        d = date(2025, 1, 1)
        results = _read_results(d, d)
        assert results == []

    def test_atomic_write_no_corrupt(self):
        from mesh_status.persistence import _append_results, _read_results

        d = date(2026, 6, 18)
        data = [{"test": "atomic", "n": i, "timestamp": 200.0 + i} for i in range(5)]
        _append_results(d, data)
        read_back = _read_results(d, d)
        assert len(read_back) >= 5
        atomic_items = [r for r in read_back if r.get("test") == "atomic"]
        assert len(atomic_items) == 5

    def test_flush_results(self):
        from mesh_status.persistence import _flush_results, _read_results

        d = date(2026, 6, 18)
        ts = datetime(2026, 6, 18, 12, 0, 0).timestamp()
        results = {
            "10.0.0.1": [
                {"node_ip": "10.0.0.1", "target_ip": "10.0.0.2", "ping_ok": True, "timestamp": ts}
            ]
        }
        _flush_results(results)
        read_back = _read_results(d, d)
        flushed = [r for r in read_back if r.get("timestamp") == ts]
        assert len(flushed) >= 1


class TestMoveOldToAggregates:
    """Tests for _move_old_to_aggregates() helper."""

    def test_mixed(self):
        from mesh_status.persistence import _move_old_to_aggregates

        now = time.time()
        cutoff = now - 50000
        results = {
            "10.0.0.1": [
                {"target_ip": "10.0.0.2", "ping_ok": True, "timestamp": now - 100},
                {"target_ip": "10.0.0.2", "ping_ok": True, "timestamp": now - 100000},
                {"target_ip": "10.0.0.3", "ping_ok": True, "timestamp": now - 200},
                {"target_ip": "10.0.0.3", "ping_ok": True, "timestamp": now - 200000},
                {"target_ip": "10.0.0.2", "ping_ok": True, "timestamp": now - 300000},
            ],
        }
        day_agg = {}
        _move_old_to_aggregates(results, day_agg, cutoff)

        assert len(results["10.0.0.1"]) == 2
        for r in results["10.0.0.1"]:
            assert r["timestamp"] >= cutoff
        assert len(day_agg) > 0

    def test_all_old(self):
        from mesh_status.persistence import _move_old_to_aggregates

        now = time.time()
        cutoff = now - 50000
        results = {
            "10.0.0.1": [
                {"target_ip": "10.0.0.2", "ping_ok": True, "timestamp": now - 100000},
            ],
        }
        day_agg = {}
        _move_old_to_aggregates(results, day_agg, cutoff)

        assert results == {}

    def test_all_recent(self):
        from mesh_status.persistence import _move_old_to_aggregates

        now = time.time()
        cutoff = now - 50000
        results = {
            "10.0.0.1": [
                {"target_ip": "10.0.0.2", "ping_ok": True, "timestamp": now - 100},
            ],
        }
        day_agg = {}
        _move_old_to_aggregates(results, day_agg, cutoff)

        assert len(results["10.0.0.1"]) == 1
        assert day_agg == {}

    def test_empty(self):
        from mesh_status.persistence import _move_old_to_aggregates

        results = {}
        day_agg = {}
        _move_old_to_aggregates(results, day_agg, 1000.0)

        assert results == {}
        assert day_agg == {}


class TestLoadIntoMemory:
    """Tests for persistence.load_into_memory()."""

    def _write_result(self, day_str: str, record: dict):
        dt = datetime.strptime(day_str, "%Y-%m-%d")
        path = Path("data") / str(dt.year) / f"{dt.month:02d}" / f"{dt.day:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")

    async def test_empty_data_dir(self):
        from mesh_status.persistence import load_into_memory

        store = {}
        agg = {}
        await load_into_memory(store, agg)
        assert store == {}
        assert agg == {}

    async def test_all_recent_data(self):
        from mesh_status.persistence import load_into_memory

        now = time.time()
        today = datetime.now().strftime("%Y-%m-%d")
        for i in range(10):
            self._write_result(
                today,
                {
                    "node_ip": "10.0.0.1",
                    "target_ip": "10.0.0.2",
                    "ping_ok": True,
                    "http_ok": True,
                    "timestamp": now - i * 3600,
                },
            )

        store = {}
        agg = {}
        await load_into_memory(store, agg)
        assert len(store) > 0
        assert len(agg) == 0

    async def test_all_old_data(self):
        from mesh_status.persistence import load_into_memory

        for offset_days in [5, 6, 7]:
            d = (datetime.now() - timedelta(days=offset_days)).strftime("%Y-%m-%d")
            ts = (datetime.now() - timedelta(days=offset_days)).timestamp()
            self._write_result(
                d,
                {
                    "node_ip": "10.0.0.1",
                    "target_ip": "10.0.0.2",
                    "ping_ok": True,
                    "http_ok": True,
                    "timestamp": ts,
                },
            )

        store = {}
        agg = {}
        await load_into_memory(store, agg)
        assert store == {}
        assert len(agg) > 0

    async def test_mixed_data(self):
        from mesh_status.persistence import load_into_memory

        now = time.time()
        today = datetime.now().strftime("%Y-%m-%d")
        old_day = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        old_ts = (datetime.now() - timedelta(days=5)).timestamp()

        for i in range(5):
            self._write_result(
                today,
                {
                    "node_ip": "10.0.0.1",
                    "target_ip": "10.0.0.2",
                    "ping_ok": True,
                    "timestamp": now - i * 3600,
                },
            )
        for i in range(5):
            self._write_result(
                old_day,
                {
                    "node_ip": "10.0.0.1",
                    "target_ip": "10.0.0.3",
                    "ping_ok": True,
                    "timestamp": old_ts,
                },
            )

        store = {}
        agg = {}
        await load_into_memory(store, agg)
        assert "10.0.0.1" in store
        assert len(store["10.0.0.1"]) == 5
        assert len(agg) > 0

    async def test_aggregation_math(self):
        from mesh_status.persistence import load_into_memory

        old_day = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
        old_ts = (datetime.now() - timedelta(days=5)).timestamp()

        for i in range(10):
            self._write_result(
                old_day,
                {
                    "node_ip": "10.0.0.1",
                    "target_ip": "10.0.0.2",
                    "ping_ok": i < 6,
                    "http_ok": i < 7,
                    "timestamp": old_ts + i,
                },
            )

        store = {}
        agg = {}
        await load_into_memory(store, agg)
        assert store == {}
        assert old_day in agg
        key = ("10.0.0.1", "10.0.0.2")
        assert key in agg[old_day]
        stats = agg[old_day][key]
        assert stats["total"] == 10
        assert stats["ping_ok"] == 6
        assert stats["http_ok"] == 7

    async def test_missing_node_ip_inference(self):
        from mesh_status.persistence import load_into_memory

        now = time.time()
        today = datetime.now().strftime("%Y-%m-%d")

        self._write_result(
            today,
            {
                "node_ip": "10.0.0.1",
                "target_ip": "10.0.0.2",
                "ping_ok": True,
                "timestamp": now - 100,
            },
        )
        self._write_result(
            today,
            {
                "target_ip": "10.0.0.2",
                "ping_ok": True,
                "timestamp": now - 200,
            },
        )

        store = {}
        agg = {}
        await load_into_memory(store, agg)
        assert "10.0.0.1" in store
        assert len(store["10.0.0.1"]) == 2

    async def test_data_beyond_90_days(self):
        from mesh_status.persistence import load_into_memory

        old_day = (datetime.now() - timedelta(days=100)).strftime("%Y-%m-%d")
        old_ts = (datetime.now() - timedelta(days=100)).timestamp()

        self._write_result(
            old_day,
            {
                "node_ip": "10.0.0.1",
                "target_ip": "10.0.0.2",
                "ping_ok": True,
                "timestamp": old_ts,
            },
        )

        store = {}
        agg = {}
        await load_into_memory(store, agg)
        assert store == {}
        assert agg == {}

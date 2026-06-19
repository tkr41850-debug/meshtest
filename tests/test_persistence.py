import json
import os
import tempfile
from datetime import date, datetime

import pytest

from mesh_status import config

# Test that config loads
def test_config_has_defaults():
    assert hasattr(config, "DEFAULT_PORT")


class TestPersistence:
    def test_ensure_data_dir_creates_path(self):
        from mesh_status.persistence import _ensure_data_dir, _date_path
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
        from datetime import datetime
        from mesh_status.persistence import _flush_results, _read_results
        import time
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

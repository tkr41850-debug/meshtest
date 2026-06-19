import time
import pytest
from datetime import datetime

from mesh_status import config


class TestStatus:
    def test_ok_status(self):
        from mesh_status.status import calculate_status
        now = 1000.0
        results = {
            "10.0.0.1": [
                {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True, "timestamp": 995.0}
            ]
        }
        registry = {"10.0.0.1": {}, "10.0.0.2": {}}
        status = calculate_status("10.0.0.1", "10.0.0.2", results, registry, now)
        assert status["ping_status"] == "OK"
        assert status["http_status"] == "OK"

    def test_pending_status(self):
        from mesh_status.status import calculate_status
        now = 1000.0
        results = {}
        registry = {"10.0.0.1": {}}
        status = calculate_status("10.0.0.1", "10.0.0.2", results, registry, now)
        assert status["ping_status"] == "Pending"
        assert status["http_status"] == "Pending"

    def test_not_available_status(self):
        from mesh_status.status import calculate_status
        now = 1000.0
        grace = getattr(config, "GRACE_PERIOD", 120)
        old_time = now - grace - 1  # 1s beyond grace period
        results = {
            "10.0.0.1": [
                {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True, "timestamp": old_time}
            ]
        }
        registry = {"10.0.0.1": {}}
        status = calculate_status("10.0.0.1", "10.0.0.2", results, registry, now)
        assert status["ping_status"] == "NotAvailable"
        assert status["http_status"] == "NotAvailable"

    def test_per_check_type_status(self):
        from mesh_status.status import calculate_status
        now = 1000.0
        results = {
            "10.0.0.1": [
                {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": False, "timestamp": 995.0}
            ]
        }
        registry = {"10.0.0.1": {}, "10.0.0.2": {}}
        status = calculate_status("10.0.0.1", "10.0.0.2", results, registry, now)
        assert status["ping_status"] == "OK"
        assert status["http_status"] == "NotAvailable"  # http check failed

    def test_target_not_in_registry(self):
        from mesh_status.status import calculate_status
        now = 1000.0
        results = {}
        registry = {"10.0.0.1": {}}
        status = calculate_status("10.0.0.1", "10.0.0.2", results, registry, now)
        assert status["ping_status"] in ("Pending", "NotAvailable")

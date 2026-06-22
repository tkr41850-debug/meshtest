import time

import pytest

pytestmark = pytest.mark.spec


class TestRegistration:
    def test_register_node_returns_peers(self, client, managed_leader):
        resp = client.post("/register", json={"node_ip": "10.0.0.1"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"
        assert "peers" in data

    def test_register_duplicate_is_idempotent(self, client, managed_leader):
        resp = client.post("/register", json={"node_ip": "10.0.0.2"})
        assert resp.status_code == 200
        resp = client.post("/register", json={"node_ip": "10.0.0.2"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "registered"

    def test_register_missing_ip_returns_400(self, client, managed_leader):
        resp = client.post("/register", json={})
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    def test_register_missing_body_returns_400(self, client, managed_leader):
        resp = client.post("/register")
        assert resp.status_code == 400


class TestNodeList:
    def test_node_list_returns_registered_nodes(self, client, managed_leader):
        client.post("/register", json={"node_ip": "10.0.0.1"})
        client.post("/register", json={"node_ip": "10.0.0.2"})
        resp = client.get("/node-list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 2
        assert len(data["nodes"]) >= 2

    def test_node_list_empty_initially(self, client, managed_leader):
        resp = client.get("/node-list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0


class TestSubmission:
    def test_submit_checks_returns_accepted(self, client, managed_leader):
        payload = {
            "node_ip": "10.0.0.1",
            "checks": [
                {
                    "target_ip": "10.0.0.2",
                    "ping_ok": True,
                    "http_ok": True,
                    "timestamp": time.time(),
                }
            ],
            "timestamp": time.time(),
        }
        resp = client.post("/submit", json=payload)
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["count"] == 1

    def test_submit_empty_body_returns_400(self, client, managed_leader):
        resp = client.post("/submit", json={})
        assert resp.status_code == 400

    def test_submit_missing_node_ip_returns_400(self, client, managed_leader):
        resp = client.post("/submit", json={"checks": [], "timestamp": time.time()})
        assert resp.status_code == 400

    def test_submit_empty_checks_returns_400(self, client, managed_leader):
        resp = client.post(
            "/submit", json={"node_ip": "10.0.0.1", "checks": [], "timestamp": time.time()}
        )
        assert resp.status_code == 400

    def test_submit_missing_timestamp_returns_400(self, client, managed_leader):
        resp = client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [{"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True}],
            },
        )
        assert resp.status_code == 400


class TestHealthEndpoints:
    def test_livez_returns_alive(self, client, managed_leader):
        resp = client.get("/livez")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    def test_readyz_returns_ready(self, client, managed_leader):
        resp = client.get("/readyz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_healthz_returns_alive(self, client, managed_leader):
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"


class TestDataQuery:
    def test_data_90m_returns_checks_and_statuses(self, client, managed_leader):
        now = time.time()
        client.post("/register", json={"node_ip": "10.0.0.1"})
        client.post("/register", json={"node_ip": "10.0.0.2"})
        client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [
                    {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True, "timestamp": now}
                ],
                "timestamp": now,
            },
        )
        resp = client.get("/data?window=90m")
        assert resp.status_code == 200
        data = resp.json()
        assert data["window"] == "90m"
        assert "checks" in data
        assert "statuses" in data
        assert "timestamp" in data

    def test_data_90h_returns_hours(self, client, managed_leader):
        now = time.time()
        client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [
                    {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True, "timestamp": now}
                ],
                "timestamp": now,
            },
        )
        resp = client.get("/data?window=90h")
        assert resp.status_code == 200
        data = resp.json()
        assert data["window"] == "90h"
        assert "hours" in data
        assert "timestamp" in data

    def test_data_90d_returns_days(self, client, managed_leader):
        now = time.time()
        client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [
                    {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True, "timestamp": now}
                ],
                "timestamp": now,
            },
        )
        resp = client.get("/data?window=90d")
        assert resp.status_code == 200
        data = resp.json()
        assert data["window"] == "90d"
        assert "days" in data
        assert "timestamp" in data

    def test_data_invalid_window_returns_400(self, client, managed_leader):
        resp = client.get("/data?window=invalid")
        assert resp.status_code == 400
        data = resp.json()
        assert "error" in data

    def test_data_missing_window_returns_400(self, client, managed_leader):
        resp = client.get("/data")
        assert resp.status_code == 400


class TestUpdateConfig:
    def test_update_config_accepts_valid_values(self, client, managed_leader):
        resp = client.post("/updateConfig", json={"check_interval": 30, "buffer_size": 5000})
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "config_updated"
        assert data["config"]["check_interval"] == 30
        assert data["config"]["buffer_size"] == 5000

    def test_update_config_empty_body_returns_400(self, client, managed_leader):
        resp = client.post("/updateConfig", json={})
        assert resp.status_code == 400

    def test_update_config_negative_interval_returns_400(self, client, managed_leader):
        resp = client.post("/updateConfig", json={"check_interval": -1})
        assert resp.status_code == 400


class TestPersistence:
    def test_data_survives_leader_restart(self, client, managed_leader):
        now = time.time()
        client.post("/register", json={"node_ip": "10.0.0.1"})
        client.post("/register", json={"node_ip": "10.0.0.2"})
        resp = client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [
                    {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True, "timestamp": now}
                ],
                "timestamp": now,
            },
        )
        assert resp.status_code == 202

        resp = client.get("/data?window=90m")
        assert resp.status_code == 200
        pre_restart_checks = len(resp.json().get("checks", []))

        managed_leader.restart()

        resp = client.get("/data?window=90m")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data.get("checks", [])) == pre_restart_checks, (
            f"Expected {pre_restart_checks} checks after restart, got {len(data.get('checks', []))}"
        )

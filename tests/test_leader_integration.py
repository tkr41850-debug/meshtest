import json
import time
from datetime import datetime, timedelta
from pathlib import Path

from mesh_status import config
from mesh_status.leader import _registry


class TestRegistrationIntegration:
    async def test_single_node_registration_returns_200(self, client):
        resp = await client.post("/register", json={"node_ip": "10.0.0.1"})
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["status"] == "registered"
        assert "peers" in data

    async def test_multi_node_registration_adds_all(self, client):
        ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
        for ip in ips:
            resp = await client.post("/register", json={"node_ip": ip})
            assert resp.status_code == 200
        assert len(_registry) == 3
        for ip in ips:
            assert ip in _registry

    async def test_re_registration_idempotent(self, client):
        resp1 = await client.post("/register", json={"node_ip": "10.0.0.1"})
        assert resp1.status_code == 200
        resp2 = await client.post("/register", json={"node_ip": "10.0.0.1"})
        assert resp2.status_code == 200
        assert len(_registry) == 1
        assert _registry["10.0.0.1"].node_ip == "10.0.0.1"

    async def test_missing_node_ip_returns_400(self, client):
        resp = await client.post("/register", json={})
        assert resp.status_code == 400
        data = await resp.get_json()
        assert "Missing node_ip" in str(data)


class TestPeerPushIntegration:
    async def test_registration_triggers_peer_push(self, client, mock_httpx):
        resp = await client.post("/register", json={"node_ip": "10.0.0.1"})
        assert resp.status_code == 200
        mock_httpx.post.assert_called()

    async def test_peer_push_sent_to_existing_nodes(self, client, mock_httpx):
        await client.post("/register", json={"node_ip": "10.0.0.1"})
        mock_httpx.post.reset_mock()
        await client.post("/register", json={"node_ip": "10.0.0.2"})
        push_urls = [call[0][0] for call in mock_httpx.post.call_args_list]
        assert any("10.0.0.1" in url for url in push_urls)
        assert any("10.0.0.2" in url for url in push_urls)

    async def test_peer_push_payload_structure(self, client, mock_httpx):
        await client.post("/register", json={"node_ip": "10.0.0.1"})
        mock_httpx.post.reset_mock()
        await client.post("/register", json={"node_ip": "10.0.0.2"})
        last_call = mock_httpx.post.call_args
        assert last_call is not None
        kwargs = last_call[1]
        payload = kwargs.get("json", {})
        assert "peers" in payload
        assert isinstance(payload["peers"], list)
        assert "check_interval" in payload
        assert "buffer_size" in payload


class TestSubmissionIntegration:
    async def test_valid_submission_returns_202(self, client):
        resp = await client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [{"target_ip": "10.0.0.2", "ping_ok": True}],
                "timestamp": 1000.0,
            },
        )
        assert resp.status_code == 202
        data = await resp.get_json()
        assert data["status"] == "accepted"

    async def test_missing_node_ip_returns_400(self, client):
        resp = await client.post(
            "/submit",
            json={
                "checks": [{"target_ip": "10.0.0.2", "ping_ok": True}],
                "timestamp": 1000.0,
            },
        )
        assert resp.status_code == 400

    async def test_missing_checks_returns_400(self, client):
        resp = await client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "timestamp": 1000.0,
            },
        )
        assert resp.status_code == 400

    async def test_bad_timestamp_returns_400(self, client):
        resp = await client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [{"target_ip": "10.0.0.2", "ping_ok": True}],
                "timestamp": "bad",
            },
        )
        assert resp.status_code == 400


class TestConfigPushIntegration:
    async def test_config_update_returns_200(self, client, mock_httpx):
        resp = await client.post("/updateConfig", json={"check_interval": 30})
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["status"] == "config_updated"
        assert data["config"]["check_interval"] == 30

    async def test_config_change_updates_state(self, client, mock_httpx):
        old_interval = config.CHECK_INTERVAL
        try:
            await client.post("/updateConfig", json={"check_interval": 99})
            assert config.CHECK_INTERVAL == 99
        finally:
            config.CHECK_INTERVAL = old_interval

    async def test_config_push_notifies_registered_nodes(self, client, mock_httpx):
        await client.post("/register", json={"node_ip": "10.0.0.1"})
        await client.post("/register", json={"node_ip": "10.0.0.2"})
        mock_httpx.post.reset_mock()
        await client.post("/updateConfig", json={"check_interval": 30})
        assert mock_httpx.post.called


class TestDataApiIntegration:
    async def test_data_90m_returns_expected_structure(self, client):
        resp = await client.get("/data?window=90m")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert "window" in data
        assert data["window"] == "90m"
        assert "checks" in data
        assert "statuses" in data
        assert "timestamp" in data

    async def test_data_90h_returns_expected_structure(self, client):
        resp = await client.get("/data?window=90h")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert "window" in data
        assert data["window"] == "90h"
        assert "hours" in data
        assert "timestamp" in data

    async def test_data_90d_returns_expected_structure(self, client):
        resp = await client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert "window" in data
        assert data["window"] == "90d"
        assert "days" in data
        assert "timestamp" in data

    async def test_data_90d_includes_in_memory_data(self, client):
        import time

        ts = time.time() - 3600
        await client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [
                    {
                        "target_ip": "10.0.0.2",
                        "ping_ok": True,
                        "http_ok": True,
                        "timestamp": ts,
                    }
                ],
                "timestamp": ts,
            },
        )
        resp = await client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert len(data["days"]) > 0
        day = data["days"][0]
        assert len(day["connections"]) > 0
        conn = day["connections"][0]
        assert conn["ping_uptime_pct"] == 100.0
        assert conn["http_uptime_pct"] == 100.0

    async def test_data_90d_aggregates_by_day(self, client):
        import time

        ts = time.time() - 3600
        await client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.2",
                "checks": [
                    {
                        "target_ip": "10.0.0.1",
                        "ping_ok": True,
                        "http_ok": False,
                        "timestamp": ts,
                    },
                    {
                        "target_ip": "10.0.0.3",
                        "ping_ok": False,
                        "http_ok": False,
                        "timestamp": ts + 0.5,
                    },
                ],
                "timestamp": ts,
            },
        )
        resp = await client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert len(data["days"]) > 0
        day = data["days"][0]
        assert len(day["connections"]) == 2
        conn_a = next(c for c in day["connections"] if c["target_ip"] == "10.0.0.1")
        assert conn_a["ping_uptime_pct"] == 100.0
        assert conn_a["http_uptime_pct"] == 0.0
        conn_b = next(c for c in day["connections"] if c["target_ip"] == "10.0.0.3")
        assert conn_b["ping_uptime_pct"] == 0.0
        assert conn_b["http_uptime_pct"] == 0.0

    async def test_data_90d_returns_empty_days_with_no_data(self, client):
        resp = await client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["days"] == []

    async def test_data_90h_returns_empty_hours_with_no_data(self, client):
        resp = await client.get("/data?window=90h")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["hours"] == []

    async def test_data_90m_accumulates_across_submissions(self, client):
        import time

        now = time.time()
        ts1 = now - 120
        ts2 = now - 60
        await client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [
                    {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True, "timestamp": ts1}
                ],
                "timestamp": ts1,
            },
        )
        await client.post(
            "/submit",
            json={
                "node_ip": "10.0.0.1",
                "checks": [
                    {"target_ip": "10.0.0.2", "ping_ok": False, "http_ok": True, "timestamp": ts2}
                ],
                "timestamp": ts2,
            },
        )
        resp = await client.get("/data?window=90m")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert len(data["checks"]) >= 2, (
            "Expected checks from both submissions (accumulated history), "
            "got only %d. If this fails, `_results[node_ip] = checks` "
            "is still replacing instead of appending." % len(data["checks"])
        )

    async def test_data_without_window_returns_400(self, client):
        resp = await client.get("/data")
        assert resp.status_code == 400


class TestCorsIntegration:
    async def test_cors_headers_on_data_endpoint(self, client):
        resp = await client.get("/data?window=90m", headers={"Origin": "http://example.com"})
        assert resp.headers.get("access-control-allow-origin") == "*"

    async def test_options_preflight_returns_cors_headers(self, client):
        resp = await client.options(
            "/data",
            headers={
                "Origin": "http://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        cors_header = resp.headers.get("access-control-allow-origin")
        assert cors_header == "*" or cors_header is not None


class TestDataReloadIntegration:
    async def test_90h_after_load_returns_from_memory(self, client):
        from mesh_status.leader import _results, _day_aggregates
        from mesh_status import persistence

        now = time.time()
        dt = datetime.now()
        path = Path("data") / str(dt.year) / f"{dt.month:02d}" / f"{dt.day:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(
                json.dumps(
                    {
                        "node_ip": "10.0.0.1",
                        "target_ip": "10.0.0.2",
                        "ping_ok": True,
                        "http_ok": True,
                        "timestamp": now - 3600,
                    }
                )
                + "\n"
            )

        await persistence.load_into_memory(_results, _day_aggregates)

        resp = await client.get("/data?window=90h")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert len(data["hours"]) > 0

    async def test_90d_after_load_returns_from_both_sources(self, client):
        from mesh_status.leader import _results, _day_aggregates
        from mesh_status import persistence

        now = time.time()
        today = datetime.now()
        old_day = datetime.now() - timedelta(days=5)

        path = Path("data") / str(today.year) / f"{today.month:02d}" / f"{today.day:02d}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(
                json.dumps(
                    {
                        "node_ip": "10.0.0.1",
                        "target_ip": "10.0.0.2",
                        "ping_ok": True,
                        "timestamp": now - 3600,
                    }
                )
                + "\n"
            )

        old_path = (
            Path("data") / str(old_day.year) / f"{old_day.month:02d}" / f"{old_day.day:02d}.json"
        )
        old_path.parent.mkdir(parents=True, exist_ok=True)
        with open(old_path, "w") as f:
            f.write(
                json.dumps(
                    {
                        "node_ip": "10.0.0.3",
                        "target_ip": "10.0.0.4",
                        "ping_ok": True,
                        "timestamp": old_day.timestamp(),
                    }
                )
                + "\n"
            )

        await persistence.load_into_memory(_results, _day_aggregates)

        resp = await client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert len(data["days"]) >= 2

    async def test_90d_aggregate_merging(self, client):
        from mesh_status.leader import _results, _day_aggregates

        today_str = datetime.now().strftime("%Y-%m-%d")
        _day_aggregates[today_str] = {
            ("10.0.0.1", "10.0.0.2"): {"total": 10, "ping_ok": 10, "http_ok": 10},
        }
        _results["10.0.0.3"] = [
            {
                "target_ip": "10.0.0.4",
                "ping_ok": True,
                "http_ok": True,
                "timestamp": time.time() - 100,
            },
        ]

        resp = await client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        all_targets = set()
        for d in data["days"]:
            if d["date"] == today_str:
                for c in d["connections"]:
                    all_targets.add(c["target_ip"])
        assert "10.0.0.2" in all_targets
        assert "10.0.0.4" in all_targets

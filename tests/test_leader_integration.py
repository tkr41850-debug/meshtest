import pytest
from unittest.mock import AsyncMock, patch

from mesh_status import config
from mesh_status.leader import _registry, _results, _peers_by_node


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
        resp = await client.post("/submit", json={
            "node_ip": "10.0.0.1",
            "checks": [{"target_ip": "10.0.0.2", "ping_ok": True}],
            "timestamp": 1000.0,
        })
        assert resp.status_code == 202
        data = await resp.get_json()
        assert data["status"] == "accepted"

    async def test_missing_node_ip_returns_400(self, client):
        resp = await client.post("/submit", json={
            "checks": [{"target_ip": "10.0.0.2", "ping_ok": True}],
            "timestamp": 1000.0,
        })
        assert resp.status_code == 400

    async def test_missing_checks_returns_400(self, client):
        resp = await client.post("/submit", json={
            "node_ip": "10.0.0.1",
            "timestamp": 1000.0,
        })
        assert resp.status_code == 400

    async def test_bad_timestamp_returns_400(self, client):
        resp = await client.post("/submit", json={
            "node_ip": "10.0.0.1",
            "checks": [{"target_ip": "10.0.0.2", "ping_ok": True}],
            "timestamp": "bad",
        })
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
        await client.post("/updateConfig", json={"check_interval": 99})
        assert config.CHECK_INTERVAL == 99
        config.CHECK_INTERVAL = old_interval

    async def test_config_push_notifies_registered_nodes(self, client, mock_httpx):
        await client.post("/register", json={"node_ip": "10.0.0.1"})
        await client.post("/register", json={"node_ip": "10.0.0.2"})
        mock_httpx.post.reset_mock()
        await client.post("/updateConfig", json={"check_interval": 30})
        assert mock_httpx.post.called


class TestDataApiIntegration:
    async def test_data_30m_returns_expected_structure(self, client):
        resp = await client.get("/data?window=30m")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert "window" in data
        assert data["window"] == "30m"
        assert "checks" in data
        assert "statuses" in data
        assert "timestamp" in data

    async def test_data_30d_returns_expected_structure(self, client):
        resp = await client.get("/data?window=30d")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert "window" in data
        assert data["window"] == "30d"
        assert "days" in data
        assert "timestamp" in data

    async def test_data_without_window_returns_400(self, client):
        resp = await client.get("/data")
        assert resp.status_code == 400


class TestCorsIntegration:
    async def test_cors_headers_on_data_endpoint(self, client):
        resp = await client.get("/data?window=30m", headers={"Origin": "http://example.com"})
        assert resp.headers.get("access-control-allow-origin") == "*"

    async def test_options_preflight_returns_cors_headers(self, client):
        resp = await client.options("/data", headers={
            "Origin": "http://example.com",
            "Access-Control-Request-Method": "GET",
        })
        cors_header = resp.headers.get("access-control-allow-origin")
        assert cors_header == "*" or cors_header is not None

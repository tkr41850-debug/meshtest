import pytest


class TestDataAPI:
    async def test_data_90m_endpoint(self):
        from mesh_status.leader import app
        test_client = app.test_client()
        resp = await test_client.get("/data?window=90m")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert "window" in data
        assert data["window"] == "90m"

    async def test_data_90d_endpoint(self):
        from mesh_status.leader import app
        test_client = app.test_client()
        resp = await test_client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["window"] == "90d"

    async def test_data_90h_endpoint(self):
        from mesh_status.leader import app
        test_client = app.test_client()
        resp = await test_client.get("/data?window=90h")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["window"] == "90h"
        assert "hours" in data

    async def test_data_missing_window(self):
        from mesh_status.leader import app
        test_client = app.test_client()
        resp = await test_client.get("/data")
        assert resp.status_code == 400

    async def test_data_invalid_window(self):
        from mesh_status.leader import app
        test_client = app.test_client()
        resp = await test_client.get("/data?window=invalid")
        assert resp.status_code == 400

    async def test_data_cors_headers(self):
        from mesh_status.leader import app
        test_client = app.test_client()
        resp = await test_client.get("/data?window=90m", headers={"Origin": "http://example.com"})
        assert resp.headers.get("access-control-allow-origin") == "*"

    async def test_data_90d_infers_node_ip_from_results(self):
        from mesh_status.leader import app, _results
        from mesh_status.persistence import _append_results, _read_results
        from datetime import date, datetime
        _results.clear()
        _results["10.0.0.1"] = [
            {
                "target_ip": "10.0.0.2",
                "ping_ok": True,
                "http_ok": True,
                "ping_latency_ms": 5.0,
                "http_latency_ms": 10.0,
                "timestamp": 1000000,
            }
        ]
        day = date.today()
        _append_results(day, [
            {
                "target_ip": "10.0.0.2",
                "ping_ok": True,
                "http_ok": True,
                "ping_latency_ms": 5.0,
                "http_latency_ms": 10.0,
                "timestamp": 1000000,
            }
        ])
        test_client = app.test_client()
        resp = await test_client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        _results.clear()
        found = False
        for day_entry in data.get("days", []):
            for conn in day_entry.get("connections", []):
                if conn.get("target_ip") == "10.0.0.2":
                    assert conn["node_ip"] == "10.0.0.1"
                    found = True
        assert found, "Expected connection with inferred node_ip not found"

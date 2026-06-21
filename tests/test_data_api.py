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
        from mesh_status.leader import app, _results, _day_aggregates

        _results.clear()
        _day_aggregates.clear()
        _day_aggregates["2026-06-01"] = {
            ("10.0.0.1", "10.0.0.2"): {"total": 100, "ping_ok": 100, "http_ok": 100},
        }
        test_client = app.test_client()
        resp = await test_client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        _results.clear()
        _day_aggregates.clear()
        found = False
        for day_entry in data.get("days", []):
            for conn in day_entry.get("connections", []):
                if conn.get("target_ip") == "10.0.0.2":
                    assert conn["node_ip"] == "10.0.0.1"
                    found = True
        assert found, "Expected connection with node_ip not found"

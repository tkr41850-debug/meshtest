class TestDataAPI:
    async def test_data_90h_includes_raw_counts(self):
        import time
        from mesh_status.leader import app, _results

        _results.clear()
        ts = time.time() - 60
        _results["10.0.0.1"] = [
            {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True, "timestamp": ts},
            {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": False, "timestamp": ts + 10},
        ]
        test_client = app.test_client()
        resp = await test_client.get("/data?window=90h")
        assert resp.status_code == 200
        data = await resp.get_json()
        hour = data["hours"][0]
        conn = hour["connections"][0]
        assert conn["ping_ok"] == 2
        assert conn["http_ok"] == 1
        assert conn["total_checks"] == 2

    async def test_data_90h_raw_counts_no_data(self):
        from mesh_status.leader import app, _results

        _results.clear()
        test_client = app.test_client()
        resp = await test_client.get("/data?window=90h")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["hours"] == []

    async def test_data_90d_includes_raw_counts(self):
        from mesh_status.leader import app, _day_aggregates

        _day_aggregates.clear()
        _day_aggregates["2026-06-01"] = {
            ("10.0.0.1", "10.0.0.2"): {"total": 10, "ping_ok": 10, "http_ok": 9},
        }
        test_client = app.test_client()
        resp = await test_client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        conn = data["days"][0]["connections"][0]
        assert conn["ping_ok"] == 10
        assert conn["http_ok"] == 9
        assert conn["total_checks"] == 10

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

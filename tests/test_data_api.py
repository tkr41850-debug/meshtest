class TestDataAPI:
    async def test_data_90h_includes_raw_counts(self, client):
        import time

        from mesh_status.leader import _results

        _results.clear()
        ts = time.time() - 60
        _results["10.0.0.1"] = [
            {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": True, "timestamp": ts},
            {"target_ip": "10.0.0.2", "ping_ok": True, "http_ok": False, "timestamp": ts + 10},
        ]
        resp = await client.get("/data?window=90h")
        assert resp.status_code == 200
        data = await resp.get_json()
        hour = data["hours"][0]
        conn = hour["connections"][0]
        assert conn["ping_ok"] == 2
        assert conn["http_ok"] == 1
        assert conn["total_checks"] == 2

    async def test_data_90h_raw_counts_no_data(self, client):
        from mesh_status.leader import _results

        _results.clear()
        resp = await client.get("/data?window=90h")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["hours"] == []

    async def test_data_90d_includes_raw_counts(self, client):
        from mesh_status.leader import _day_aggregates

        _day_aggregates.clear()
        _day_aggregates["2026-06-01"] = {
            ("10.0.0.1", "10.0.0.2"): {"total": 10, "ping_ok": 10, "http_ok": 9},
        }
        resp = await client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        conn = data["days"][0]["connections"][0]
        assert conn["ping_ok"] == 10
        assert conn["http_ok"] == 9
        assert conn["total_checks"] == 10

    async def test_data_90m_endpoint(self, client):
        resp = await client.get("/data?window=90m")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert "window" in data
        assert data["window"] == "90m"

    async def test_data_90d_endpoint(self, client):
        resp = await client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["window"] == "90d"

    async def test_data_90h_endpoint(self, client):
        resp = await client.get("/data?window=90h")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["window"] == "90h"
        assert "hours" in data

    async def test_data_missing_window(self, client):
        resp = await client.get("/data")
        assert resp.status_code == 400

    async def test_data_invalid_window(self, client):
        resp = await client.get("/data?window=invalid")
        assert resp.status_code == 400

    async def test_data_cors_headers(self, client):
        resp = await client.get("/data?window=90m", headers={"Origin": "http://example.com"})
        assert resp.headers.get("access-control-allow-origin") == "*"

    async def test_data_90d_no_duplicate_dates(self, client):
        import time

        from mesh_status.leader import _day_aggregates, _results

        _results.clear()
        _day_aggregates.clear()
        today_str = "2026-06-01"
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
        dates = [d["date"] for d in data["days"]]
        date_counts = {}
        for d in dates:
            date_counts[d] = date_counts.get(d, 0) + 1
        for d, count in date_counts.items():
            assert count == 1, f"Duplicate date entry found: {d} appears {count} times"

    async def test_update_config_rejects_non_int(self, client):
        resp = await client.post("/updateConfig", json={"check_interval": "abc"})
        assert resp.status_code == 400

    async def test_update_config_rejects_negative(self, client):
        resp = await client.post("/updateConfig", json={"check_interval": -1})
        assert resp.status_code == 400

    async def test_zero_total_checks_does_not_crash(self, client):
        from mesh_status.leader import _day_aggregates

        _day_aggregates.clear()
        _day_aggregates["2026-06-01"] = {
            ("10.0.0.1", "10.0.0.2"): {"total": 0, "ping_ok": 0, "http_ok": 0},
        }
        resp = await client.get("/data?window=90d")
        assert resp.status_code == 200
        data = await resp.get_json()
        conn = data["days"][0]["connections"][0]
        assert conn["ping_uptime_pct"] == 0.0
        assert conn["http_uptime_pct"] == 0.0

    async def test_data_90d_infers_node_ip_from_results(self, client):
        from mesh_status.leader import _day_aggregates, _results

        _results.clear()
        _day_aggregates.clear()
        _day_aggregates["2026-06-01"] = {
            ("10.0.0.1", "10.0.0.2"): {"total": 100, "ping_ok": 100, "http_ok": 100},
        }
        resp = await client.get("/data?window=90d")
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

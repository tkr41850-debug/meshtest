import pytest


class TestDataAPI:
    async def test_data_30m_endpoint(self):
        from mesh_status.leader import app
        test_client = app.test_client()
        resp = await test_client.get("/data?window=30m")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert "window" in data
        assert data["window"] == "30m"

    async def test_data_30d_endpoint(self):
        from mesh_status.leader import app
        test_client = app.test_client()
        resp = await test_client.get("/data?window=30d")
        assert resp.status_code == 200
        data = await resp.get_json()
        assert data["window"] == "30d"

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
        resp = await test_client.get("/data?window=30m", headers={"Origin": "http://example.com"})
        assert resp.headers.get("access-control-allow-origin") == "*"

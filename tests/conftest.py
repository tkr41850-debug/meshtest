import os
import shutil
import pytest
from unittest.mock import Mock, patch, AsyncMock


@pytest.fixture(autouse=True)
def reset_leader_state():
    from mesh_status.leader import _registry, _results, _peers_by_node
    _registry.clear()
    _results.clear()
    _peers_by_node.clear()
    # Remove stale disk data from previous runs
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    if os.path.isdir(data_dir):
        shutil.rmtree(data_dir)


@pytest.fixture
def app():
    from mesh_status.leader import app as leader_app
    return leader_app


@pytest.fixture
async def client(app):
    async with app.test_client() as c:
        yield c


@pytest.fixture
async def registered_nodes(client):
    node_ips = ["10.0.0.1", "10.0.0.2", "10.0.0.3"]
    for ip in node_ips:
        resp = await client.post("/register", json={"node_ip": ip})
        assert resp.status_code == 200
    return node_ips


@pytest.fixture
def mock_httpx():
    with patch("mesh_status.leader.httpx.AsyncClient") as mock_cls:
        mock_instance = AsyncMock()
        mock_cls.return_value.__aenter__.return_value = mock_instance
        mock_response = AsyncMock()
        mock_response.raise_for_status = Mock()
        mock_instance.post = AsyncMock(return_value=mock_response)
        yield mock_instance

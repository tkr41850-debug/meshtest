import streamlit as st
from unittest.mock import patch, MagicMock

from mesh_status import dashboard


def setup_function():
    st.cache_data.clear()


def test_fetch_node_list_normalizes_dict_format():
    with patch("mesh_status.dashboard.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "nodes": [{"ip": "10.0.0.1", "port": 58080}, {"ip": "10.0.0.2", "port": 58081}]
        }
        mock_get.return_value = mock_resp
        mock_get.return_value.raise_for_status = lambda: None

        nodes = dashboard.fetch_node_list()

        assert nodes == ["10.0.0.1", "10.0.0.2"]


def test_fetch_node_list_passes_through_bare_strings():
    with patch("mesh_status.dashboard.requests.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"nodes": ["10.0.0.1", "10.0.0.2"]}
        mock_get.return_value = mock_resp
        mock_get.return_value.raise_for_status = lambda: None

        nodes = dashboard.fetch_node_list()

        assert nodes == ["10.0.0.1", "10.0.0.2"]

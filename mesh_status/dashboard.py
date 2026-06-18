import os
import time
from datetime import datetime

import requests
import streamlit as st

LEADER_URL = os.environ.get("LEADER_URL", "http://localhost:58080")
DATA_FETCH_TIMEOUT = 5


@st.cache_data(ttl=30)
def fetch_data_30m():
    try:
        resp = requests.get(f"{LEADER_URL}/data?window=30m", timeout=DATA_FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=30)
def fetch_data_30d():
    try:
        resp = requests.get(f"{LEADER_URL}/data?window=30d", timeout=DATA_FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException:
        return None


@st.cache_data(ttl=30)
def fetch_node_list():
    try:
        resp = requests.get(f"{LEADER_URL}/node-list", timeout=DATA_FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("nodes", [])
    except requests.RequestException:
        return []


def fetch_all_data():
    data_30m = fetch_data_30m()
    data_30d = fetch_data_30d()
    nodes = fetch_node_list()
    leader_ok = data_30m is not None
    return data_30m, data_30d, nodes, leader_ok


st.set_page_config(page_title="mesh-status", page_icon="\U0001f310", layout="wide")
st.title("mesh-status")


@st.fragment
def render_dashboard():
    pass


render_dashboard()

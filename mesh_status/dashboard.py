import html
import logging
import os
import time
from datetime import datetime as dt

import requests
import streamlit as st

logger = logging.getLogger(__name__)

LEADER_URL = "http://localhost:58080"
DATA_FETCH_TIMEOUT = 5
REFRESH_INTERVAL = 30


@st.cache_data(ttl=25)  # slightly less than fragment sleep (30s) to ensure fresh fetch
def fetch_data_30m():
    try:
        resp = requests.get(f"{LEADER_URL}/data?window=30m", timeout=DATA_FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("Failed to fetch 30m data from leader: %s", e)
        return None


@st.cache_data(ttl=25)  # slightly less than fragment sleep (30s) to ensure fresh fetch
def fetch_data_30d():
    try:
        resp = requests.get(f"{LEADER_URL}/data?window=30d", timeout=DATA_FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.warning("Failed to fetch 30d data from leader: %s", e)
        return None


@st.cache_data(ttl=25)  # slightly less than fragment sleep (30s) to ensure fresh fetch
def fetch_node_list():
    try:
        resp = requests.get(f"{LEADER_URL}/node-list", timeout=DATA_FETCH_TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("nodes", [])
    except requests.RequestException as e:
        logger.warning("Failed to fetch node list from leader: %s", e)
        return []


def fetch_all_data():
    data_30m = fetch_data_30m()
    data_30d = fetch_data_30d()
    nodes = fetch_node_list()
    leader_ok = data_30m is not None
    return data_30m, data_30d, nodes, leader_ok


def _render_connectivity_matrix(combined, nodes):
    html_parts = ['<div style="overflow-x: auto; margin-bottom: 12px;">']
    html_parts.append('<table style="border-collapse: collapse; font-size: 13px;">')
    html_parts.append('<tr>')
    html_parts.append(
        '<th style="padding: 4px 8px; text-align: left; font-weight: 600; '
        'color: #374151; background: #f3f4f6; border: 1px solid #e5e7eb;">'
        'Src \\ Target</th>'
    )
    for tgt_ip in nodes:
        short = tgt_ip.rsplit(".", 1)[-1]
        html_parts.append(
            f'<th style="padding: 4px 8px; text-align: center; font-weight: 600; '
            f'color: #374151; background: #f3f4f6; border: 1px solid #e5e7eb; '
            f'font-family: monospace;">{html.escape(short)}</th>'
        )
    html_parts.append('</tr>')
    for src_ip in nodes:
        html_parts.append('<tr>')
        html_parts.append(
            f'<td style="padding: 4px 8px; font-family: monospace; color: #374151; '
            f'border: 1px solid #e5e7eb; white-space: nowrap;">{html.escape(src_ip)}</td>'
        )
        for tgt_ip in nodes:
            html_parts.append(
                '<td style="padding: 4px 8px; text-align: center; border: 1px solid #e5e7eb;">'
            )
            if src_ip == tgt_ip:
                html_parts.append('<span style="color: #9ca3af;">\u2014</span>')
            else:
                status = combined.get((src_ip, tgt_ip), "Pending")
                if status == "OK":
                    html_parts.append('<span style="color: #22c55e; font-size: 18px;">\u25cf</span>')
                elif status == "NotAvailable":
                    html_parts.append('<span style="color: #f59e0b; font-size: 18px;">\u25cf</span>')
                else:
                    html_parts.append('<span style="color: #9ca3af; font-size: 18px;">\u25cf</span>')
            html_parts.append('</td>')
        html_parts.append('</tr>')
    html_parts.append('</table></div>')
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _build_uptime_map(data_30d) -> dict:
    uptime = {}
    if not data_30d or not data_30d.get("days"):
        return uptime
    for day_data in data_30d["days"]:
        for conn in day_data.get("connections", []):
            key = (conn.get("node_ip"), conn.get("target_ip"))
            uptime[key] = max(
                conn.get("ping_uptime_pct", 0),
                conn.get("http_uptime_pct", 0),
            )
    return uptime


def _render_detail_card(tgt_ip, status, ping_lat, http_lat, last_seen, uptime_pct):
    if status == "OK":
        border_color = "#22c55e"
        badge_color = "#22c55e"
        badge = "OK"
    elif status == "NotAvailable":
        border_color = "#f59e0b"
        badge_color = "#f59e0b"
        badge = "Not Available"
    else:
        border_color = "#9ca3af"
        badge_color = "#9ca3af"
        badge = "Pending"

    uptime_html = ""
    if uptime_pct is not None:
        if uptime_pct >= 99:
            uptime_color = "#22c55e"
        elif uptime_pct >= 95:
            uptime_color = "#f59e0b"
        else:
            uptime_color = "#ef4444"
        uptime_html = f'<span style="color:{uptime_color}; font-weight:600;">{uptime_pct:.1f}% uptime</span>'

    card = f"""<div style="
    border: 1px solid #e5e7eb;
    border-left: 4px solid {border_color};
    border-radius: 8px;
    padding: 10px 14px;
    margin-bottom: 8px;
    background: #ffffff;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
">
    <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 4px;">
        <span style="
            display: inline-block;
            background: {badge_color};
            color: white;
            padding: 2px 10px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.3px;
        ">{badge}</span>
        <span style="font-family: monospace; font-size: 14px; font-weight: 600; color: #1f2937;">{html.escape(tgt_ip)}</span>
    </div>
    <div style="font-size: 12px; color: #6b7280; display: flex; gap: 16px; flex-wrap: wrap;">
        <span>Ping: <strong style="color:#374151;">{ping_lat}</strong></span>
        <span>HTTP: <strong style="color:#374151;">{http_lat}</strong></span>
        <span>Last: <strong style="color:#374151;">{last_seen}</strong></span>
        {uptime_html}
    </div>
</div>"""
    st.markdown(card, unsafe_allow_html=True)


def _render_30m_view(data_30m, nodes, data_30d=None):
    if not nodes:
        st.markdown('<p style="color: #6b7280;">No nodes registered \u2014 run mesh-register on each VM</p>', unsafe_allow_html=True)
        return

    if data_30m is None:
        st.markdown('<p style="color: #6b7280;">No data available for this time window</p>', unsafe_allow_html=True)
        return

    combined = {}
    for s in data_30m.get("statuses", []):
        src = s.get("node_ip")
        tgt = s.get("target_ip")
        ping = s.get("ping_status")
        http = s.get("http_status")
        if not all([src, tgt, ping, http]):
            continue
        if ping == "OK" and http == "OK":
            combined[(src, tgt)] = "OK"
        elif ping == "NotAvailable" or http == "NotAvailable":
            combined[(src, tgt)] = "NotAvailable"
        else:
            combined[(src, tgt)] = "Pending"

    latencies = {}
    for c in data_30m.get("checks", []):
        key = (c.get("node_ip"), c.get("target_ip"))
        if key not in latencies or c.get("timestamp", 0) > latencies[key].get("timestamp", 0):
            latencies[key] = c

    uptime_map = _build_uptime_map(data_30d) if data_30d else {}

    sorted_nodes = sorted(nodes)

    if len(sorted_nodes) >= 2:
        st.markdown("##### Connectivity Matrix")
        _render_connectivity_matrix(combined, sorted_nodes)

    for src_ip in sorted_nodes:
        targets_ok = sum(1 for tgt in sorted_nodes if src_ip != tgt and combined.get((src_ip, tgt)) == "OK")
        targets_total = sum(1 for tgt in sorted_nodes if src_ip != tgt)

        if targets_total == 0:
            summary = "No targets"
        elif targets_ok == targets_total:
            summary = "All OK"
        elif targets_ok == 0:
            summary = "Pending"
        else:
            summary = f"{targets_total - targets_ok} of {targets_total} down"

        with st.expander(f"\u25b6 {src_ip}  [{summary}]  \u2014  {targets_total} targets"):
            for tgt_ip in sorted_nodes:
                if src_ip == tgt_ip:
                    continue

                status = combined.get((src_ip, tgt_ip), "Pending")
                check = latencies.get((src_ip, tgt_ip), {})
                ping_lat = f'{check["ping_latency_ms"]:.1f}ms' if check.get("ping_latency_ms") is not None else "\u2014"
                http_lat = f'{check["http_latency_ms"]:.1f}ms' if check.get("http_latency_ms") is not None else "\u2014"
                last_seen = dt.fromtimestamp(check["timestamp"]).strftime("%H:%M:%S") if check.get("timestamp") else "\u2014"
                uptime_pct = uptime_map.get((src_ip, tgt_ip))

                _render_detail_card(tgt_ip, status, ping_lat, http_lat, last_seen, uptime_pct)


def _render_30d_view(data_30d, nodes):
    if data_30d is None or not data_30d.get("days"):
        st.markdown('<p style="color: #6b7280;">No data available for this time window</p>', unsafe_allow_html=True)
        return

    for src_ip in sorted(nodes):
        with st.expander(f"\u25b6 {src_ip}"):
            has_data = False
            for day_data in data_30d["days"]:
                date_label = day_data["date"]
                src_connections = [c for c in day_data.get("connections", []) if c.get("node_ip") == src_ip]
                if not src_connections:
                    cols = st.columns([1.5, 1, 1, 1, 1])
                    cols[0].markdown(date_label)
                    cols[1].markdown('<span style="color:#9ca3af;">\u2014</span>', unsafe_allow_html=True)
                    cols[2].markdown("\u2014")
                    cols[3].markdown("\u2014")
                    cols[4].markdown("0")
                    continue

                has_data = True
                for conn in src_connections:
                    ping_pct = conn.get("ping_uptime_pct", 0)
                    http_pct = conn.get("http_uptime_pct", 0)
                    total = conn.get("total_checks", 0)

                    best_pct = max(ping_pct, http_pct)
                    if best_pct >= 99:
                        badge = f'<span style="background:#22c55e; color:white; padding:2px 8px; border-radius:4px; font-size:12px;">{best_pct:.1f}%</span>'
                    elif best_pct >= 95:
                        badge = f'<span style="background:#f59e0b; color:white; padding:2px 8px; border-radius:4px; font-size:12px;">{best_pct:.1f}%</span>'
                    else:
                        badge = f'<span style="background:#ef4444; color:white; padding:2px 8px; border-radius:4px; font-size:12px;">{best_pct:.1f}%</span>'

                    cols = st.columns([1.5, 1, 1, 1, 1])
                    cols[0].markdown(f'{date_label} \u2192 {conn.get("target_ip", "\u2014")}')
                    cols[1].markdown(badge, unsafe_allow_html=True)
                    cols[2].markdown(f"{ping_pct:.1f}%")
                    cols[3].markdown(f"{http_pct:.1f}%")
                    cols[4].markdown(str(total))

            if not has_data:
                st.markdown('<p style="color: #6b7280;">No data for this node</p>', unsafe_allow_html=True)


def _render_refresh_indicator(leader_ok):
    now_str = dt.now().strftime("%H:%M:%S")
    st.markdown(
        f'<p style="color: #9ca3af; font-size: 14px; text-align: center;">'
        f'\U0001f504 Auto-refreshing every 30s  |  Last update: {now_str}'
        f'</p>',
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="mesh-status", page_icon="\U0001f310", layout="wide")
st.title("mesh-status")

# Tabs created outside the fragment so they persist across reruns (fixes WR-02)
tab1, tab2 = st.tabs(["30-Minute View", "30-Day View"])

with tab1:
    tab1_placeholder = st.empty()

with tab2:
    tab2_placeholder = st.empty()

refresh_indicator_placeholder = st.empty()


@st.fragment
def render_dashboard():
    data_30m, data_30d, nodes, leader_ok = fetch_all_data()

    if not leader_ok:
        st.warning("\u26a0 Leader unreachable \u2014 showing cached data")

    with tab1_placeholder.container():
        _render_30m_view(data_30m, nodes, data_30d)

    with tab2_placeholder.container():
        _render_30d_view(data_30d, nodes)

    with refresh_indicator_placeholder.container():
        _render_refresh_indicator(leader_ok)

    time.sleep(REFRESH_INTERVAL)
    st.rerun()


with st.spinner("Loading mesh data..."):
    render_dashboard()

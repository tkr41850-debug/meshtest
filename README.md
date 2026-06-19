# mesh-status

A distributed mesh connectivity testing tool for monitoring network health across VMs connected via VPN WAN.

## Dashboard

The dashboard provides real-time (30-minute) and historical (30-day) views of mesh connectivity.

**Prerequisites:**
- Python 3.12+
- Install the package: `pip install -e .`

**Environment Variables:**
| Variable | Description | Example |
|----------|-------------|---------|
| `LEADER_URL` | URL of the leader node's HTTP API | `http://10.0.0.1:58080` |

**Run the dashboard:**
```bash
LEADER_URL=http://<leader-ip>:58080 streamlit run mesh_status/dashboard.py --server.port 58581
```

Open `http://localhost:58581` (or the host IP) in a browser.

#!/usr/bin/env python3
"""Register a node with a mesh-status leader."""

import argparse
import json
import sys
import urllib.request
import urllib.error


def parse_args():
    parser = argparse.ArgumentParser(description="Register a node with mesh-status leader")
    parser.add_argument("--node-ip", "-n", help="This node's IP address")
    parser.add_argument("--leader-ip", "-l", help="Leader server's IP address")
    parser.add_argument(
        "--port", "-p", type=int, default=58080, help="Leader port (default: 58080)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    node_ip = args.node_ip
    leader_ip = args.leader_ip

    if not node_ip:
        node_ip = input("Enter node IP: ").strip()
    if not leader_ip:
        leader_ip = input("Enter leader IP: ").strip()

    url = f"http://{leader_ip}:{args.port}/register"
    payload = json.dumps({"node_ip": node_ip}).encode("utf-8")

    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            print(f"Registered successfully. Peers: {body.get('peers', [])}")
            sys.exit(0)
    except urllib.error.HTTPError as e:
        print(f"Registration failed (HTTP {e.code}): {e.read().decode('utf-8')}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Registration failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

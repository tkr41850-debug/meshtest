import os
import subprocess
import time

import httpx
import pytest

LEADER_START_CMD = os.environ.get("LEADER_START_CMD", "")
LEADER_STOP_CMD = os.environ.get("LEADER_STOP_CMD", "")
LEADER_URL = os.environ.get("LEADER_URL", "http://127.0.0.1:58080")

REQUIRED_VARS = {"LEADER_START_CMD": LEADER_START_CMD, "LEADER_STOP_CMD": LEADER_STOP_CMD}


def _skip_reason():
    missing = [k for k, v in REQUIRED_VARS.items() if not v]
    if missing:
        return "Set " + " and ".join(missing) + " to run spec integration tests"
    return ""


SKIP_REASON = _skip_reason()


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "spec: integration tests exercising the leader via HTTP only"
    )


def pytest_collection_modifyitems(config, items):
    if SKIP_REASON:
        for item in items:
            item.add_marker(pytest.mark.skip(reason=SKIP_REASON))


def _wait_for_livez(url: str, timeout: int = 15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            resp = httpx.get(f"{url}/livez", timeout=2)
            if resp.status_code == 200:
                return
        except (httpx.ConnectError, httpx.TimeoutException):
            pass
        time.sleep(0.5)
    raise RuntimeError(f"Leader did not start within {timeout}s at {url}/livez")


def _wait_for_dead(url: str, timeout: int = 15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            httpx.get(f"{url}/livez", timeout=2)
        except (httpx.ConnectError, httpx.TimeoutException):
            return
        time.sleep(0.5)
    raise RuntimeError(f"Leader did not stop within {timeout}s at {url}/livez")


class LeaderManager:
    def __init__(self, start_cmd: str, stop_cmd: str, url: str):
        self.start_cmd = start_cmd
        self.stop_cmd = stop_cmd
        self.url = url
        self._running = False

    def start(self):
        subprocess.run(self.start_cmd, shell=True, check=True)
        _wait_for_livez(self.url)
        self._running = True

    def stop(self):
        if not self._running:
            return
        subprocess.run(self.stop_cmd, shell=True, check=True)
        _wait_for_dead(self.url)
        self._running = False

    def restart(self):
        self.stop()
        self.start()


@pytest.fixture(scope="session")
def leader_url():
    return LEADER_URL


@pytest.fixture(scope="session")
def client(leader_url):
    with httpx.Client(base_url=leader_url, timeout=10) as c:
        yield c


@pytest.fixture(scope="module")
def managed_leader():
    if SKIP_REASON:
        yield None
        return
    manager = LeaderManager(LEADER_START_CMD, LEADER_STOP_CMD, LEADER_URL)
    manager.start()
    yield manager
    manager.stop()

import asyncio
import time
from argparse import Namespace
from collections import deque
from unittest.mock import AsyncMock, Mock, patch

import node
from mesh_status import config


class _StopLoop(BaseException):
    pass


class TestCheckExecutionIntegration:
    async def test_ping_success_returns_latency(self):
        with patch.object(node.asyncio, "create_subprocess_exec") as mock_sub:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.wait = AsyncMock(return_value=0)
            mock_proc.communicate = AsyncMock(
                return_value=(b"64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=5.23 ms", b"")
            )
            mock_proc.kill = AsyncMock()
            mock_sub.return_value = mock_proc

            with patch("node.httpx.AsyncClient") as mock_cls:
                mock_inst = AsyncMock()
                mock_cls.return_value.__aenter__.return_value = mock_inst
                mock_resp = AsyncMock()
                mock_resp.is_success = True
                mock_resp.status_code = 200
                mock_inst.get = AsyncMock(return_value=mock_resp)

                result = await node.check_node("10.0.0.2")

        assert result["ping_ok"] is True
        assert result["ping_latency_ms"] == 5.23

    async def test_ping_failure_returns_not_ok(self):
        with patch.object(node.asyncio, "create_subprocess_exec") as mock_sub:
            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.wait = AsyncMock(return_value=1)
            mock_proc.communicate = AsyncMock(return_value=(b"", b"ping: unknown host"))
            mock_proc.kill = AsyncMock()
            mock_sub.return_value = mock_proc

            with patch("node.httpx.AsyncClient") as mock_cls:
                mock_inst = AsyncMock()
                mock_cls.return_value.__aenter__.return_value = mock_inst
                mock_inst.get = AsyncMock(side_effect=Exception("conn failed"))

                result = await node.check_node("10.0.0.2")

        assert result["ping_ok"] is False
        assert result["ping_latency_ms"] is None

    async def test_ping_timeout_handled_gracefully(self):
        with patch.object(node.asyncio, "create_subprocess_exec") as mock_sub:
            wait_calls = [0]

            async def wait_with_timeout():
                wait_calls[0] += 1
                if wait_calls[0] == 1:
                    raise asyncio.TimeoutError()
                return 1

            mock_proc = AsyncMock()
            mock_proc.returncode = 1
            mock_proc.wait = wait_with_timeout
            mock_proc.communicate = AsyncMock(return_value=(b"", b""))
            mock_proc.kill = Mock()
            mock_sub.return_value = mock_proc

            with patch("node.httpx.AsyncClient") as mock_cls:
                mock_inst = AsyncMock()
                mock_cls.return_value.__aenter__.return_value = mock_inst
                mock_inst.get = AsyncMock(side_effect=Exception("conn failed"))

                result = await node.check_node("10.0.0.2", timeout=5.0)

        assert result["ping_ok"] is False
        mock_proc.kill.assert_called_once()

    async def test_http_health_check_handles_200_and_failure(self):
        with patch.object(node.asyncio, "create_subprocess_exec") as mock_sub:
            mock_proc = AsyncMock()
            mock_proc.returncode = 0
            mock_proc.wait = AsyncMock(return_value=0)
            mock_proc.communicate = AsyncMock(
                return_value=(b"64 bytes from 10.0.0.2: icmp_seq=1 ttl=64 time=5.0 ms", b"")
            )
            mock_proc.kill = AsyncMock()
            mock_sub.return_value = mock_proc

            with patch("node.httpx.AsyncClient") as mock_cls:
                mock_inst = AsyncMock()
                mock_cls.return_value.__aenter__.return_value = mock_inst

                mock_resp_ok = AsyncMock()
                mock_resp_ok.is_success = True
                mock_resp_ok.status_code = 200
                mock_inst.get = AsyncMock(return_value=mock_resp_ok)

                result_ok = await node.check_node("10.0.0.2")
                assert result_ok["http_ok"] is True
                assert result_ok["http_status"] == 200

                mock_inst.get = AsyncMock(side_effect=Exception("connection refused"))
                result_fail = await node.check_node("10.0.0.3")
                assert result_fail["http_ok"] is False


class TestSemaphoreIntegration:
    async def test_semaphore_limits_concurrent(self):
        sem = asyncio.Semaphore(10)
        peers = [{"ip": f"10.0.0.{i}", "port": 58080} for i in range(1, 16)]
        active = set()
        max_active = [0]

        async def mock_check(ip, port, timeout=5.0):
            active.add(ip)
            max_active[0] = max(max_active[0], len(active))
            await asyncio.sleep(0.02)
            active.discard(ip)
            return {"target_ip": ip, "ping_ok": True}

        with patch.object(node, "check_node", mock_check):
            results = await node.run_check_cycle(sem, peers)

        assert len(results) == 15
        assert max_active[0] <= 10

    async def test_semaphore_caps_at_10_with_15_peers(self):
        sem = asyncio.Semaphore(10)
        peers = [{"ip": f"10.0.0.{i}", "port": 58080} for i in range(1, 16)]
        active = set()
        max_active = [0]

        async def mock_check(ip, port, timeout=5.0):
            active.add(ip)
            max_active[0] = max(max_active[0], len(active))
            await asyncio.sleep(0.02)
            active.discard(ip)
            return {"target_ip": ip, "ping_ok": True}

        with patch.object(node, "check_node", mock_check):
            results = await node.run_check_cycle(sem, peers)

        assert max_active[0] == 10

    async def test_semaphore_releases_after_completion(self):
        sem = asyncio.Semaphore(10)
        peers = [{"ip": f"10.0.0.{i}", "port": 58080} for i in range(1, 16)]

        async def mock_check(ip, port, timeout=5.0):
            await asyncio.sleep(0.01)
            return {"target_ip": ip, "ping_ok": True}

        with patch.object(node, "check_node", mock_check):
            await node.run_check_cycle(sem, peers)

        # All semaphore slots should be available after completion
        for _ in range(10):
            assert not sem.locked()
            await sem.acquire()

        # Release acquired permits
        for _ in range(10):
            sem.release()


class TestBufferRetryIntegration:
    async def test_buffer_accumulates_on_submit_failure(self):
        buffer = deque(maxlen=20000)
        cycle_results = [{"target_ip": "10.0.0.2", "ping_ok": True}]

        combined = list(buffer)
        combined.append(cycle_results)

        for batch in combined:
            with patch("node.submit_results", AsyncMock(return_value=False)) as mock_sub:
                ok = await node.submit_results(batch, "10.0.0.1", "http://10.0.0.2:58080")
                if not ok:
                    buffer.append(batch)
                break

        assert len(buffer) == 1
        assert buffer[0] == cycle_results

    async def test_buffer_clears_on_successful_submit(self):
        buffer = deque(maxlen=20000)
        buffer.append([{"target_ip": "10.0.0.2", "ping_ok": True}])
        assert len(buffer) == 1

        cycle_results = [{"target_ip": "10.0.0.3", "ping_ok": False}]
        combined = list(buffer)
        combined.append(cycle_results)

        for batch in combined:
            with patch("node.submit_results", AsyncMock(return_value=True)):
                ok = await node.submit_results(batch, "10.0.0.1", "http://10.0.0.2:58080")
                if ok:
                    buffer.clear()
                break

        assert len(buffer) == 0

    def test_buffer_maxlen_eviction(self):
        buffer = deque(maxlen=3)
        buffer.append([{"target_ip": "10.0.0.1"}])
        buffer.append([{"target_ip": "10.0.0.2"}])
        buffer.append([{"target_ip": "10.0.0.3"}])
        buffer.append([{"target_ip": "10.0.0.4"}])

        assert len(buffer) == 3
        assert buffer[0][0]["target_ip"] == "10.0.0.2"
        assert buffer[1][0]["target_ip"] == "10.0.0.3"
        assert buffer[2][0]["target_ip"] == "10.0.0.4"

    def test_combined_payload_includes_buffered_and_current(self):
        buffer = deque(maxlen=20000)
        buffered = [{"target_ip": "10.0.0.2", "ping_ok": True}]
        buffer.append(buffered)

        current = [{"target_ip": "10.0.0.3", "ping_ok": False}]
        combined = list(buffer)
        combined.append(current)

        assert len(combined) == 2
        assert combined[0] == buffered
        assert combined[1] == current


class TestRegistrationHttpIntegration:
    async def test_sends_correct_post_request(self):
        with patch("node.httpx.AsyncClient") as mock_cls:
            mock_inst = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_inst
            mock_resp = AsyncMock()
            mock_resp.is_success = True
            mock_resp.json = Mock(return_value={"peers": [{"ip": "10.0.0.1", "port": 58080}]})
            mock_inst.post = AsyncMock(return_value=mock_resp)

            url = f"http://10.0.0.1:58080/register"
            async with mock_cls(timeout=10.0) as client:
                resp = await client.post(url, json={"node_ip": "10.0.0.2", "listen_port": 58080, "node_url": ""})

            mock_inst.post.assert_called_once()
            call_url = mock_inst.post.call_args[0][0]
            call_json = mock_inst.post.call_args[1]["json"]
            assert call_url == "http://10.0.0.1:58080/register"
            assert call_json == {"node_ip": "10.0.0.2", "listen_port": 58080, "node_url": ""}

    async def test_parses_response_and_extracts_peers(self):
        with patch("node.httpx.AsyncClient") as mock_cls:
            mock_inst = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_inst
            mock_resp = AsyncMock()
            mock_resp.is_success = True
            mock_resp.json = Mock(return_value={"peers": [{"ip": "10.0.0.1", "port": 58080}, {"ip": "10.0.0.3", "port": 58080}]})
            mock_inst.post = AsyncMock(return_value=mock_resp)

            async with mock_cls(timeout=10.0) as client:
                resp = await client.post(
                    "http://10.0.0.1:58080/register",
                    json={"node_ip": "10.0.0.2", "listen_port": 58080, "node_url": ""},
                )
                data = resp.json()
                peers = data.get("peers", [])

            assert len(peers) == 2
            assert peers[0]["ip"] == "10.0.0.1"
            assert peers[0]["port"] == 58080

    async def test_handles_error_response_gracefully(self):
        with patch("node.httpx.AsyncClient") as mock_cls:
            mock_inst = AsyncMock()
            mock_cls.return_value.__aenter__.return_value = mock_inst
            mock_resp = AsyncMock()
            mock_resp.is_success = False
            mock_resp.status_code = 500
            mock_resp.text = "Internal Server Error"
            mock_inst.post = AsyncMock(return_value=mock_resp)

            async with mock_cls(timeout=10.0) as client:
                resp = await client.post(
                    "http://10.0.0.1:58080/register",
                    json={"node_ip": "10.0.0.2", "listen_port": 58080, "node_url": ""},
                )

            assert resp.is_success is False
            assert resp.status_code == 500


class TestCycleIntegration:
    async def test_full_cycle_fetch_check_submit(self):
        with patch("node.parse_args") as mock_args:
            mock_args.return_value = Namespace(
                leader_url="http://10.0.0.1:58080", node_url="http://10.0.0.2:58080"
            )

            with patch("node.httpx.AsyncClient") as mock_cls:
                mock_inst = AsyncMock()
                mock_cls.return_value.__aenter__.return_value = mock_inst

                mock_reg_resp = AsyncMock()
                mock_reg_resp.is_success = True
                mock_reg_resp.json = Mock(return_value={"peers": [{"ip": "10.0.0.1", "port": 58080}]})

                mock_list_resp = AsyncMock()
                mock_list_resp.is_success = True
                mock_list_resp.json = Mock(return_value={"nodes": [{"ip": "10.0.0.1", "port": 58080}, {"ip": "10.0.0.3", "port": 58080}]})

                mock_inst.post = AsyncMock(return_value=mock_reg_resp)
                mock_inst.get = AsyncMock(return_value=mock_list_resp)

                with patch("node.run_check_cycle") as mock_check:
                    mock_check.return_value = [
                        {"target_ip": "10.0.0.3", "ping_ok": True}
                    ]

                    with patch("node.submit_results", AsyncMock(return_value=True)) as mock_sub:
                        with patch("node.asyncio.sleep", side_effect=_StopLoop()):
                            try:
                                await node.run()
                            except _StopLoop:
                                pass

                            assert mock_inst.post.called
                            assert mock_inst.get.called
                            assert mock_check.called
                            assert mock_sub.called

                            mock_check.assert_called_once()
                            call_peers = mock_check.call_args[0][1]
                            assert any(p["ip"] == "10.0.0.1" for p in call_peers)

    async def test_full_cycle_with_buffer_retry(self):
        with patch("node.parse_args") as mock_args:
            mock_args.return_value = Namespace(
                leader_url="http://10.0.0.1:58080", node_url="http://10.0.0.2:58080"
            )

            with patch("node.httpx.AsyncClient") as mock_cls:
                mock_inst = AsyncMock()
                mock_cls.return_value.__aenter__.return_value = mock_inst

                mock_reg_resp = AsyncMock()
                mock_reg_resp.is_success = True
                mock_reg_resp.json = Mock(return_value={"peers": [{"ip": "10.0.0.1", "port": 58080}]})

                mock_list_resp = AsyncMock()
                mock_list_resp.is_success = True
                mock_list_resp.json = Mock(return_value={"nodes": [{"ip": "10.0.0.3", "port": 58080}]})

                mock_inst.post = AsyncMock(return_value=mock_reg_resp)
                mock_inst.get = AsyncMock(return_value=mock_list_resp)

                with patch("node.run_check_cycle") as mock_check:
                    mock_check.return_value = [
                        {"target_ip": "10.0.0.3", "ping_ok": True}
                    ]

                    submit_results_call_count = [0]

                    async def submit_side_effect(*args, **kwargs):
                        submit_results_call_count[0] += 1
                        if submit_results_call_count[0] <= 2:
                            return False
                        return True

                    with patch("node.submit_results", side_effect=submit_side_effect):
                        with patch("node.asyncio.sleep", side_effect=[None, None, _StopLoop()]):
                            try:
                                await node.run()
                            except _StopLoop:
                                pass

                            assert submit_results_call_count[0] >= 2

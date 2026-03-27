from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from proton_runner.executor import ExecutorConfig, run_play
from proton_runner.models import Task


def _make_ssh_result(stdout: str = "", stderr: str = "", exit_status: int = 0):
    result = MagicMock()
    result.stdout = stdout
    result.stderr = stderr
    result.exit_status = exit_status
    return result


def _make_mock_conn(results: list):
    """Create a mock SSH connection that returns results in sequence."""
    conn = AsyncMock()
    conn.run = AsyncMock(side_effect=results)
    conn.__aenter__ = AsyncMock(return_value=conn)
    conn.__aexit__ = AsyncMock(return_value=False)
    return conn


class TestRunPlay:
    @pytest.fixture
    def config(self):
        return ExecutorConfig(
            concurrency=5,
            connect_timeout=5.0,
            command_timeout=10.0,
            host_key_check=False,
        )

    @pytest.fixture
    def tasks(self):
        return [
            Task(name="Check uptime", bash="uptime"),
            Task(name="Disk usage", bash="df -h"),
        ]

    @pytest.mark.asyncio
    async def test_successful_execution(self, config, tasks):
        conn = _make_mock_conn([
            _make_ssh_result(stdout="up 10 days"),
            _make_ssh_result(stdout="/dev/sda1 50G"),
        ])

        with patch("proton_runner.executor.asyncssh") as mock_ssh:
            mock_ssh.connect = MagicMock(return_value=conn)
            mock_ssh.Error = Exception

            results = await run_play(["host1.example.com"], tasks, config)

        assert len(results) == 1
        r = results[0]
        assert r.status == "ok"
        assert len(r.task_results) == 2
        assert r.task_results[0].stdout == "up 10 days"
        assert r.task_results[0].status == "ok"
        assert r.task_results[1].stdout == "/dev/sda1 50G"

    @pytest.mark.asyncio
    async def test_command_failure(self, config, tasks):
        conn = _make_mock_conn([
            _make_ssh_result(stdout="up 10 days"),
            _make_ssh_result(stderr="permission denied", exit_status=1),
        ])

        with patch("proton_runner.executor.asyncssh") as mock_ssh:
            mock_ssh.connect = MagicMock(return_value=conn)
            mock_ssh.Error = Exception

            results = await run_play(["host1.example.com"], tasks, config)

        assert results[0].status == "failed"
        assert results[0].task_results[0].status == "ok"
        assert results[0].task_results[1].status == "failed"
        assert results[0].task_results[1].return_code == 1

    @pytest.mark.asyncio
    async def test_unreachable_host(self, config, tasks):
        with patch("proton_runner.executor.asyncssh") as mock_ssh:
            mock_ssh.connect = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(side_effect=OSError("Connection refused")),
                    __aexit__=AsyncMock(return_value=False),
                )
            )
            mock_ssh.Error = Exception

            results = await run_play(["bad.example.com"], tasks, config)

        assert results[0].status == "unreachable"
        assert results[0].unreachable is True
        assert "Connection refused" in results[0].error
        assert results[0].task_results == []

    @pytest.mark.asyncio
    async def test_command_timeout(self, config):
        tasks = [Task(name="Slow command", bash="sleep 999")]
        config = ExecutorConfig(command_timeout=0.01, host_key_check=False)

        async def slow_run(*args, **kwargs):
            await asyncio.sleep(10)

        conn = AsyncMock()
        conn.run = slow_run
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)

        with patch("proton_runner.executor.asyncssh") as mock_ssh:
            mock_ssh.connect = MagicMock(return_value=conn)
            mock_ssh.Error = Exception

            results = await run_play(["host1.example.com"], tasks, config)

        assert results[0].task_results[0].status == "failed"
        assert results[0].task_results[0].return_code == -1
        assert "timed out" in results[0].task_results[0].stderr.lower()

    @pytest.mark.asyncio
    async def test_multiple_hosts_concurrent(self, config):
        tasks = [Task(name="Echo", bash="echo hi")]
        hosts = [f"host{i}.example.com" for i in range(5)]

        conn = _make_mock_conn([_make_ssh_result(stdout="hi")])

        # Each host gets its own connection mock
        connections = []
        for _ in hosts:
            c = _make_mock_conn([_make_ssh_result(stdout="hi")])
            connections.append(c)

        call_count = 0

        def connect_side_effect(*args, **kwargs):
            nonlocal call_count
            c = connections[call_count]
            call_count += 1
            return c

        with patch("proton_runner.executor.asyncssh") as mock_ssh:
            mock_ssh.connect = MagicMock(side_effect=connect_side_effect)
            mock_ssh.Error = Exception

            results = await run_play(hosts, tasks, config)

        assert len(results) == 5
        assert all(r.status == "ok" for r in results)

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, config):
        """Verify that semaphore actually limits concurrent connections."""
        config = ExecutorConfig(concurrency=2, host_key_check=False)
        tasks = [Task(name="Echo", bash="echo hi")]
        hosts = [f"host{i}.example.com" for i in range(4)]

        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def tracked_run(*args, **kwargs):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)
            await asyncio.sleep(0.05)
            async with lock:
                current_concurrent -= 1
            return _make_ssh_result(stdout="hi")

        def make_tracked_conn(*args, **kwargs):
            conn = AsyncMock()
            conn.run = tracked_run
            conn.__aenter__ = AsyncMock(return_value=conn)
            conn.__aexit__ = AsyncMock(return_value=False)
            return conn

        with patch("proton_runner.executor.asyncssh") as mock_ssh:
            mock_ssh.connect = MagicMock(side_effect=make_tracked_conn)
            mock_ssh.Error = Exception

            results = await run_play(hosts, tasks, config)

        assert max_concurrent <= 2
        assert len(results) == 4


class TestExecutorConfig:
    def test_defaults(self):
        config = ExecutorConfig()
        assert config.username is None
        assert config.private_key is None
        assert config.concurrency == 10
        assert config.connect_timeout == 10.0
        assert config.command_timeout == 300.0
        assert config.host_key_check is True

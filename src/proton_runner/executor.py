from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import asyncssh

from proton_runner.models import HostResult, Task, TaskResult


@dataclass(frozen=True)
class ExecutorConfig:
    """Configuration for the SSH executor."""

    username: str | None = None
    private_key: str | None = None
    concurrency: int = 10
    connect_timeout: float = 10.0
    command_timeout: float = 300.0
    host_key_check: bool = True


async def run_play(
    hosts: list[str],
    tasks: list[Task],
    config: ExecutorConfig,
) -> list[HostResult]:
    """Execute tasks on all hosts concurrently, tasks sequential per host.

    Concurrency is bounded by config.concurrency via a semaphore.
    Returns one HostResult per host, in the same order as the hosts list.
    """
    semaphore = asyncio.Semaphore(config.concurrency)
    coros = [_run_on_host(semaphore, host, tasks, config) for host in hosts]
    results: list[HostResult] = await asyncio.gather(*coros)
    return results


async def _run_on_host(
    semaphore: asyncio.Semaphore,
    host: str,
    tasks: list[Task],
    config: ExecutorConfig,
) -> HostResult:
    """Open one SSH session to a host, run all tasks sequentially, then close."""
    async with semaphore:
        connect_kwargs = _build_connect_kwargs(host, config)

        try:
            async with asyncssh.connect(**connect_kwargs) as conn:
                return await _execute_tasks(conn, host, tasks, config)
        except (OSError, asyncssh.Error) as exc:
            return HostResult(host=host, unreachable=True, error=str(exc))


def _build_connect_kwargs(host: str, config: ExecutorConfig) -> dict:
    kwargs: dict = {
        "host": host,
        "login_timeout": config.connect_timeout,
    }

    if config.username:
        kwargs["username"] = config.username

    if config.private_key:
        kwargs["client_keys"] = [config.private_key]

    if not config.host_key_check:
        kwargs["known_hosts"] = None

    return kwargs


async def _execute_tasks(
    conn: asyncssh.SSHClientConnection,
    host: str,
    tasks: list[Task],
    config: ExecutorConfig,
) -> HostResult:
    """Run tasks sequentially on an established connection."""
    task_results: list[TaskResult] = []

    for task in tasks:
        try:
            result = await asyncio.wait_for(
                conn.run(task.bash, check=False),
                timeout=config.command_timeout,
            )
            task_results.append(
                TaskResult(
                    task_name=task.name,
                    host=host,
                    stdout=result.stdout or "",
                    stderr=result.stderr or "",
                    return_code=result.exit_status or 0,
                )
            )
        except asyncio.TimeoutError:
            task_results.append(
                TaskResult(
                    task_name=task.name,
                    host=host,
                    stdout="",
                    stderr=f"Command timed out after {config.command_timeout}s",
                    return_code=-1,
                )
            )

    return HostResult(host=host, task_results=task_results)

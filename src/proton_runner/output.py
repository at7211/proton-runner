from __future__ import annotations

import sys
from typing import TextIO

from proton_runner.models import HostResult, TaskResult

_GREEN = "\033[32m"
_RED = "\033[31m"
_YELLOW = "\033[33m"
_CYAN = "\033[36m"
_BOLD = "\033[1m"
_RESET = "\033[0m"


def _use_color(stream: TextIO) -> bool:
    return hasattr(stream, "isatty") and stream.isatty()


def _color(text: str, code: str, stream: TextIO) -> str:
    if not _use_color(stream):
        return text
    return f"{code}{text}{_RESET}"


def _status_color(status: str, stream: TextIO) -> str:
    colors = {"ok": _GREEN, "failed": _RED, "unreachable": _YELLOW}
    return _color(status, colors.get(status, ""), stream)


def print_play_header(hosts_group: str, stream: TextIO = sys.stdout) -> None:
    header = f"PLAY [{hosts_group}]"
    separator = "*" * max(60, len(header) + 4)
    print(file=stream)
    print(_color(separator, _BOLD, stream), file=stream)
    print(_color(header, _BOLD, stream), file=stream)
    print(_color(separator, _BOLD, stream), file=stream)


def print_task_header(task_name: str, stream: TextIO = sys.stdout) -> None:
    print(file=stream)
    print(
        _color(f"TASK [{task_name}]", _BOLD, stream),
        file=stream,
    )
    print("-" * max(60, len(task_name) + 10), file=stream)


def print_task_result(result: TaskResult, stream: TextIO = sys.stdout) -> None:
    status = _status_color(result.status, stream)
    host = _color(result.host, _CYAN, stream)
    print(f"{status} | {host}", file=stream)

    if result.stdout.strip():
        for line in result.stdout.strip().splitlines():
            print(f"    {line}", file=stream)

    if result.stderr.strip():
        for line in result.stderr.strip().splitlines():
            print(f"    {_color('stderr:', _RED, stream)} {line}", file=stream)


def print_host_unreachable(result: HostResult, stream: TextIO = sys.stdout) -> None:
    status = _status_color("unreachable", stream)
    host = _color(result.host, _CYAN, stream)
    error = result.error or "unknown error"
    print(f"{status} | {host} | {error}", file=stream)


def print_play_recap(results: list[HostResult], stream: TextIO = sys.stdout) -> None:
    ok = sum(1 for r in results if r.status == "ok")
    failed = sum(1 for r in results if r.status == "failed")
    unreachable = sum(1 for r in results if r.status == "unreachable")

    print(file=stream)
    print(_color("PLAY RECAP", _BOLD, stream), file=stream)
    print("=" * 60, file=stream)
    print(
        f"  {_color(f'ok={ok}', _GREEN, stream)}    "
        f"{_color(f'failed={failed}', _RED, stream)}    "
        f"{_color(f'unreachable={unreachable}', _YELLOW, stream)}",
        file=stream,
    )


def print_results(
    hosts_group: str,
    results: list[HostResult],
    stream: TextIO = sys.stdout,
) -> None:
    """Print full output for a play execution."""
    print_play_header(hosts_group, stream)

    reachable = [r for r in results if not r.unreachable]
    unreachable = [r for r in results if r.unreachable]

    # Collect task names from the first reachable host (all ran the same tasks)
    task_names: list[str] = []
    if reachable:
        task_names = [tr.task_name for tr in reachable[0].task_results]

    for task_idx, task_name in enumerate(task_names):
        print_task_header(task_name, stream)
        for host_result in reachable:
            if task_idx < len(host_result.task_results):
                print_task_result(host_result.task_results[task_idx], stream)

    if unreachable:
        print(file=stream)
        for host_result in unreachable:
            print_host_unreachable(host_result, stream)

    print_play_recap(results, stream)

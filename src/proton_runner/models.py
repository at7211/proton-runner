from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Task:
    """A single bash task to execute on a remote host."""

    name: str
    bash: str


@dataclass(frozen=True)
class Play:
    """A play targeting a host group with a list of tasks."""

    hosts: str
    tasks: list[Task]


@dataclass
class TaskResult:
    """Result of executing a single task on a single host."""

    task_name: str
    host: str
    stdout: str
    stderr: str
    return_code: int

    @property
    def status(self) -> str:
        return "ok" if self.return_code == 0 else "failed"


@dataclass
class HostResult:
    """Aggregate result of all tasks executed on a single host."""

    host: str
    task_results: list[TaskResult] = field(default_factory=list)
    unreachable: bool = False
    error: str | None = None

    @property
    def status(self) -> str:
        if self.unreachable:
            return "unreachable"
        if any(tr.status == "failed" for tr in self.task_results):
            return "failed"
        return "ok"

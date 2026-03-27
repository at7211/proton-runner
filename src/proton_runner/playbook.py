from __future__ import annotations

from pathlib import Path

import yaml

from proton_runner.models import Play, Task


def parse_playbook(path: str | Path) -> list[Play]:
    """Parse a YAML playbook file into a list of Play objects.

    Expected format:
        ---
        - hosts: group_name
          tasks:
            - name: Task description
              bash: command_to_run

    Raises FileNotFoundError if the file does not exist.
    Raises ValueError on any structural or validation error.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Playbook file not found: {path}")

    raw = path.read_text()
    try:
        data = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise ValueError(f"Invalid YAML in {path}: {exc}") from exc

    if not isinstance(data, list):
        raise ValueError(
            f"Playbook must be a YAML list of plays, got {type(data).__name__}"
        )

    plays: list[Play] = []
    for play_idx, play_data in enumerate(data, start=1):
        plays.append(_parse_play(play_data, play_idx))

    return plays


def _parse_play(play_data: object, play_idx: int) -> Play:
    """Validate and convert a raw dict into a Play."""
    if not isinstance(play_data, dict):
        raise ValueError(
            f"Play #{play_idx}: expected a mapping, got {type(play_data).__name__}"
        )

    if "hosts" not in play_data:
        raise ValueError(f"Play #{play_idx}: missing required field 'hosts'")
    hosts = play_data["hosts"]
    if not isinstance(hosts, str) or not hosts.strip():
        raise ValueError(f"Play #{play_idx}: 'hosts' must be a non-empty string")

    if "tasks" not in play_data:
        raise ValueError(f"Play #{play_idx}: missing required field 'tasks'")
    raw_tasks = play_data["tasks"]
    if not isinstance(raw_tasks, list) or len(raw_tasks) == 0:
        raise ValueError(f"Play #{play_idx}: 'tasks' must be a non-empty list")

    tasks: list[Task] = []
    for task_idx, task_data in enumerate(raw_tasks, start=1):
        tasks.append(_parse_task(task_data, play_idx, task_idx))

    return Play(hosts=hosts.strip(), tasks=tasks)


def _parse_task(task_data: object, play_idx: int, task_idx: int) -> Task:
    """Validate and convert a raw dict into a Task."""
    label = f"Play #{play_idx}, Task #{task_idx}"

    if not isinstance(task_data, dict):
        raise ValueError(
            f"{label}: expected a mapping, got {type(task_data).__name__}"
        )

    if "name" not in task_data:
        raise ValueError(f"{label}: missing required field 'name'")
    name = task_data["name"]
    if not isinstance(name, str) or not name.strip():
        raise ValueError(f"{label}: 'name' must be a non-empty string")

    if "bash" not in task_data:
        raise ValueError(f"{label}: missing required field 'bash'")
    bash = task_data["bash"]
    if not isinstance(bash, str) or not bash.strip():
        raise ValueError(f"{label}: 'bash' must be a non-empty string")

    return Task(name=name.strip(), bash=bash.strip())

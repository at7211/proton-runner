from __future__ import annotations

import re
from pathlib import Path

_GROUP_HEADER = re.compile(r"^\[([A-Za-z0-9_-]+)\]\s*$")

DEFAULT_INVENTORY_PATH = "/etc/playbook/hosts"


def parse_inventory(path: str | Path) -> dict[str, list[str]]:
    """Parse an INI-style inventory file into a mapping of group names to host lists.

    Format:
        [group_name]
        host1.example.com
        host2.example.com

    Blank lines and lines starting with '#' are ignored.
    Duplicate hosts within a group are deduplicated while preserving order.
    """
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"Inventory file not found: {path}")

    groups: dict[str, list[str]] = {}
    current_group: str | None = None
    seen: set[str] = set()

    for line_num, raw_line in enumerate(path.read_text().splitlines(), start=1):
        line = raw_line.strip()

        if not line or line.startswith("#"):
            continue

        header_match = _GROUP_HEADER.match(line)
        if header_match:
            current_group = header_match.group(1)
            if current_group not in groups:
                groups[current_group] = []
            seen = set(groups[current_group])
            continue

        if current_group is None:
            raise ValueError(
                f"Inventory parse error at line {line_num}: "
                f"host '{line}' appears before any group header"
            )

        if line not in seen:
            groups[current_group].append(line)
            seen.add(line)

    return groups


def resolve_hosts(inventory: dict[str, list[str]], group: str) -> list[str]:
    """Resolve a host group name to its list of hosts.

    Raises KeyError with a helpful message listing available groups.
    """
    if group not in inventory:
        available = ", ".join(sorted(inventory)) or "(none)"
        raise KeyError(
            f"Host group '{group}' not found in inventory. "
            f"Available groups: {available}"
        )
    return inventory[group]

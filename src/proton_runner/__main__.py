from __future__ import annotations

import asyncio
import getpass
import sys

from proton_runner.cli import config_from_args, parse_args
from proton_runner.executor import run_play
from proton_runner.inventory import parse_inventory, resolve_hosts
from proton_runner.models import Play
from proton_runner.output import print_results
from proton_runner.playbook import parse_playbook


async def _run_all_plays(
    plays: list[Play],
    inventory: dict[str, list[str]],
    config,
) -> tuple[bool, bool]:
    """Execute all plays, returning (has_failure, has_unreachable)."""
    has_failure = False
    has_unreachable = False

    for play in plays:
        hosts = resolve_hosts(inventory, play.hosts)
        results = await run_play(hosts, play.tasks, config)
        print_results(play.hosts, results, play.tasks)

        for r in results:
            if r.status == "failed":
                has_failure = True
            elif r.status == "unreachable":
                has_unreachable = True

    return has_failure, has_unreachable


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        inventory = parse_inventory(args.inventory)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading inventory: {exc}", file=sys.stderr)
        return 1

    try:
        plays = parse_playbook(args.playbook)
    except (FileNotFoundError, ValueError) as exc:
        print(f"Error loading playbook: {exc}", file=sys.stderr)
        return 1

    password = None
    if args.ask_pass:
        password = getpass.getpass("SSH password: ")

    config = config_from_args(args, password=password)

    try:
        has_failure, has_unreachable = asyncio.run(
            _run_all_plays(plays, inventory, config)
        )
    except KeyError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if has_unreachable:
        return 2
    if has_failure:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

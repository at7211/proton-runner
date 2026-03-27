from __future__ import annotations

import asyncio
import sys

from proton_runner.cli import config_from_args, parse_args
from proton_runner.executor import run_play
from proton_runner.inventory import parse_inventory, resolve_hosts
from proton_runner.output import print_results
from proton_runner.playbook import parse_playbook


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

    config = config_from_args(args)

    has_failure = False
    has_unreachable = False

    for play in plays:
        try:
            hosts = resolve_hosts(inventory, play.hosts)
        except KeyError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        results = asyncio.run(run_play(hosts, play.tasks, config))
        print_results(play.hosts, results)

        for r in results:
            if r.status == "failed":
                has_failure = True
            elif r.status == "unreachable":
                has_unreachable = True

    if has_unreachable:
        return 2
    if has_failure:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

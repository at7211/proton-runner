from __future__ import annotations

import argparse
import getpass

from proton_runner.executor import ExecutorConfig
from proton_runner.inventory import DEFAULT_INVENTORY_PATH


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="proton-runner",
        description="Run tasks on multiple servers via SSH using YAML playbooks.",
    )

    parser.add_argument(
        "playbook",
        help="Path to the YAML playbook file",
    )
    parser.add_argument(
        "-i",
        "--inventory",
        default=DEFAULT_INVENTORY_PATH,
        help=f"Path to the inventory hosts file (default: {DEFAULT_INVENTORY_PATH})",
    )
    parser.add_argument(
        "-u",
        "--user",
        default=None,
        help=f"SSH username (default: current user '{getpass.getuser()}')",
    )
    parser.add_argument(
        "--private-key",
        default=None,
        help="Path to SSH private key file",
    )
    parser.add_argument(
        "-c",
        "--concurrency",
        type=int,
        default=10,
        help="Maximum number of concurrent host connections (default: 10)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="SSH connection timeout in seconds (default: 10)",
    )
    parser.add_argument(
        "--command-timeout",
        type=float,
        default=300.0,
        help="Per-command execution timeout in seconds (default: 300)",
    )
    parser.add_argument(
        "-k",
        "--ask-pass",
        action="store_true",
        default=False,
        help="Prompt for SSH password",
    )
    parser.add_argument(
        "--no-host-key-check",
        action="store_true",
        default=False,
        help="Disable SSH host key verification (insecure, for testing only)",
    )

    return parser


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = build_parser()
    return parser.parse_args(argv)


def config_from_args(
    args: argparse.Namespace, password: str | None = None
) -> ExecutorConfig:
    return ExecutorConfig(
        username=args.user,
        private_key=args.private_key,
        password=password,
        concurrency=args.concurrency,
        connect_timeout=args.timeout,
        command_timeout=args.command_timeout,
        host_key_check=not args.no_host_key_check,
    )

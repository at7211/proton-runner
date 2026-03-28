from __future__ import annotations

import pytest

from proton_runner.cli import config_from_args, parse_args


class TestParseArgs:
    def test_minimal_args(self):
        args = parse_args(["playbook.yml"])
        assert args.playbook == "playbook.yml"
        assert args.inventory == "/etc/playbook/hosts"
        assert args.user is None
        assert args.private_key is None
        assert args.concurrency == 10
        assert args.timeout == 10.0
        assert args.command_timeout == 300.0
        assert args.ask_pass is False
        assert args.no_host_key_check is False

    def test_all_flags(self):
        args = parse_args([
            "play.yml",
            "-i", "/custom/hosts",
            "-u", "deploy",
            "--private-key", "/path/to/key",
            "-c", "20",
            "--timeout", "30",
            "--command-timeout", "60",
            "-k",
            "--no-host-key-check",
        ])
        assert args.playbook == "play.yml"
        assert args.inventory == "/custom/hosts"
        assert args.user == "deploy"
        assert args.private_key == "/path/to/key"
        assert args.concurrency == 20
        assert args.timeout == 30.0
        assert args.command_timeout == 60.0
        assert args.ask_pass is True
        assert args.no_host_key_check is True

    def test_missing_playbook_exits(self):
        with pytest.raises(SystemExit):
            parse_args([])


class TestConfigFromArgs:
    def test_conversion(self):
        args = parse_args([
            "play.yml",
            "-u", "admin",
            "--private-key", "/key",
            "-c", "5",
            "--timeout", "15",
            "--command-timeout", "120",
            "--no-host-key-check",
        ])
        config = config_from_args(args)
        assert config.username == "admin"
        assert config.private_key == "/key"
        assert config.concurrency == 5
        assert config.connect_timeout == 15.0
        assert config.command_timeout == 120.0
        assert config.host_key_check is False

    def test_defaults(self):
        args = parse_args(["play.yml"])
        config = config_from_args(args)
        assert config.username is None
        assert config.private_key is None
        assert config.password is None
        assert config.concurrency == 10
        assert config.host_key_check is True

    def test_password_passed_through(self):
        args = parse_args(["play.yml"])
        config = config_from_args(args, password="secret")
        assert config.password == "secret"

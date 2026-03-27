from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from proton_runner.__main__ import main
from proton_runner.models import HostResult, TaskResult
from proton_runner.output import print_results


class TestMainEntryPoint:
    def test_missing_inventory_file(self, tmp_path):
        playbook = tmp_path / "play.yml"
        playbook.write_text(
            "- hosts: web\n  tasks:\n    - name: T\n      bash: echo\n"
        )
        rc = main([str(playbook), "-i", str(tmp_path / "nope")])
        assert rc == 1

    def test_missing_playbook_file(self, tmp_path):
        hosts = tmp_path / "hosts"
        hosts.write_text("[web]\nhost.com\n")
        rc = main([str(tmp_path / "nope.yml"), "-i", str(hosts)])
        assert rc == 1

    def test_invalid_playbook(self, tmp_path):
        hosts = tmp_path / "hosts"
        hosts.write_text("[web]\nhost.com\n")
        playbook = tmp_path / "bad.yml"
        playbook.write_text("{{invalid")
        rc = main([str(playbook), "-i", str(hosts)])
        assert rc == 1

    def test_missing_host_group(self, tmp_path):
        hosts = tmp_path / "hosts"
        hosts.write_text("[web]\nhost.com\n")
        playbook = tmp_path / "play.yml"
        playbook.write_text(
            "- hosts: nonexistent\n  tasks:\n    - name: T\n      bash: echo\n"
        )
        rc = main([str(playbook), "-i", str(hosts)])
        assert rc == 1

    def test_successful_run(self, tmp_path):
        hosts = tmp_path / "hosts"
        hosts.write_text("[web]\nhost.com\n")
        playbook = tmp_path / "play.yml"
        playbook.write_text(
            "- hosts: web\n  tasks:\n    - name: Hello\n      bash: echo hi\n"
        )

        conn = AsyncMock()
        result = MagicMock()
        result.stdout = "hi"
        result.stderr = ""
        result.exit_status = 0
        conn.run = AsyncMock(return_value=result)
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)

        with patch("proton_runner.executor.asyncssh") as mock_ssh:
            mock_ssh.connect = MagicMock(return_value=conn)
            mock_ssh.Error = Exception
            rc = main([str(playbook), "-i", str(hosts)])

        assert rc == 0

    def test_failed_run_returns_1(self, tmp_path):
        hosts = tmp_path / "hosts"
        hosts.write_text("[web]\nhost.com\n")
        playbook = tmp_path / "play.yml"
        playbook.write_text(
            "- hosts: web\n  tasks:\n    - name: Fail\n      bash: exit 1\n"
        )

        conn = AsyncMock()
        result = MagicMock()
        result.stdout = ""
        result.stderr = "error"
        result.exit_status = 1
        conn.run = AsyncMock(return_value=result)
        conn.__aenter__ = AsyncMock(return_value=conn)
        conn.__aexit__ = AsyncMock(return_value=False)

        with patch("proton_runner.executor.asyncssh") as mock_ssh:
            mock_ssh.connect = MagicMock(return_value=conn)
            mock_ssh.Error = Exception
            rc = main([str(playbook), "-i", str(hosts)])

        assert rc == 1

    def test_unreachable_returns_2(self, tmp_path):
        hosts = tmp_path / "hosts"
        hosts.write_text("[web]\nhost.com\n")
        playbook = tmp_path / "play.yml"
        playbook.write_text(
            "- hosts: web\n  tasks:\n    - name: T\n      bash: echo\n"
        )

        with patch("proton_runner.executor.asyncssh") as mock_ssh:
            mock_ssh.connect = MagicMock(
                return_value=AsyncMock(
                    __aenter__=AsyncMock(side_effect=OSError("refused")),
                    __aexit__=AsyncMock(return_value=False),
                )
            )
            mock_ssh.Error = Exception
            rc = main([str(playbook), "-i", str(hosts)])

        assert rc == 2


class TestOutputFormatting:
    def test_successful_output(self):
        buf = io.StringIO()
        results = [
            HostResult(
                host="host1.com",
                task_results=[
                    TaskResult(
                        task_name="Uptime",
                        host="host1.com",
                        stdout="up 10 days",
                        stderr="",
                        return_code=0,
                    ),
                ],
            ),
        ]
        print_results("web", results, stream=buf)
        output = buf.getvalue()
        assert "PLAY [web]" in output
        assert "TASK [Uptime]" in output
        assert "ok" in output
        assert "up 10 days" in output
        assert "ok=1" in output
        assert "failed=0" in output

    def test_failed_output(self):
        buf = io.StringIO()
        results = [
            HostResult(
                host="host1.com",
                task_results=[
                    TaskResult(
                        task_name="Bad",
                        host="host1.com",
                        stdout="",
                        stderr="no such file",
                        return_code=2,
                    ),
                ],
            ),
        ]
        print_results("db", results, stream=buf)
        output = buf.getvalue()
        assert "failed" in output
        assert "no such file" in output
        assert "failed=1" in output

    def test_unreachable_output(self):
        buf = io.StringIO()
        results = [
            HostResult(host="bad.com", unreachable=True, error="Connection refused"),
        ]
        print_results("db", results, stream=buf)
        output = buf.getvalue()
        assert "unreachable" in output
        assert "Connection refused" in output
        assert "unreachable=1" in output

from __future__ import annotations

import pytest

from proton_runner.models import Play, Task
from proton_runner.playbook import parse_playbook


class TestParsePlaybook:
    def test_single_play(self, tmp_file):
        path = tmp_file(
            "---\n"
            "- hosts: dbservers\n"
            "  tasks:\n"
            "    - name: Check uptime\n"
            "      bash: uptime\n",
            name="playbook.yml",
        )
        plays = parse_playbook(path)
        assert len(plays) == 1
        assert plays[0].hosts == "dbservers"
        assert len(plays[0].tasks) == 1
        assert plays[0].tasks[0] == Task(name="Check uptime", bash="uptime")

    def test_multiple_plays(self, tmp_file):
        path = tmp_file(
            "---\n"
            "- hosts: web\n"
            "  tasks:\n"
            "    - name: T1\n"
            "      bash: echo web\n"
            "- hosts: db\n"
            "  tasks:\n"
            "    - name: T2\n"
            "      bash: echo db\n",
            name="playbook.yml",
        )
        plays = parse_playbook(path)
        assert len(plays) == 2
        assert plays[0].hosts == "web"
        assert plays[1].hosts == "db"

    def test_multiple_tasks(self, tmp_file):
        path = tmp_file(
            "- hosts: servers\n"
            "  tasks:\n"
            "    - name: A\n"
            "      bash: cmd_a\n"
            "    - name: B\n"
            "      bash: cmd_b\n"
            "    - name: C\n"
            "      bash: cmd_c\n",
            name="playbook.yml",
        )
        plays = parse_playbook(path)
        assert len(plays[0].tasks) == 3
        assert [t.name for t in plays[0].tasks] == ["A", "B", "C"]

    def test_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            parse_playbook(tmp_path / "nope.yml")

    def test_invalid_yaml(self, tmp_file):
        path = tmp_file("{{invalid yaml", name="bad.yml")
        with pytest.raises(ValueError, match="Invalid YAML"):
            parse_playbook(path)

    def test_not_a_list(self, tmp_file):
        path = tmp_file("hosts: web\n", name="playbook.yml")
        with pytest.raises(ValueError, match="must be a YAML list"):
            parse_playbook(path)

    def test_play_missing_hosts(self, tmp_file):
        path = tmp_file(
            "- tasks:\n" "    - name: T\n" "      bash: echo\n",
            name="playbook.yml",
        )
        with pytest.raises(ValueError, match="missing required field 'hosts'"):
            parse_playbook(path)

    def test_play_missing_tasks(self, tmp_file):
        path = tmp_file("- hosts: web\n", name="playbook.yml")
        with pytest.raises(ValueError, match="missing required field 'tasks'"):
            parse_playbook(path)

    def test_empty_tasks_list(self, tmp_file):
        path = tmp_file("- hosts: web\n  tasks: []\n", name="playbook.yml")
        with pytest.raises(ValueError, match="must be a non-empty list"):
            parse_playbook(path)

    def test_task_missing_name(self, tmp_file):
        path = tmp_file(
            "- hosts: web\n" "  tasks:\n" "    - bash: echo\n",
            name="playbook.yml",
        )
        with pytest.raises(ValueError, match="missing required field 'name'"):
            parse_playbook(path)

    def test_task_missing_bash(self, tmp_file):
        path = tmp_file(
            "- hosts: web\n" "  tasks:\n" "    - name: T\n",
            name="playbook.yml",
        )
        with pytest.raises(ValueError, match="missing required field 'bash'"):
            parse_playbook(path)

    def test_play_not_a_dict(self, tmp_file):
        path = tmp_file("- just a string\n", name="playbook.yml")
        with pytest.raises(ValueError, match="expected a mapping"):
            parse_playbook(path)

    def test_task_not_a_dict(self, tmp_file):
        path = tmp_file(
            "- hosts: web\n" "  tasks:\n" "    - just a string\n",
            name="playbook.yml",
        )
        with pytest.raises(ValueError, match="expected a mapping"):
            parse_playbook(path)

    def test_hosts_not_string(self, tmp_file):
        path = tmp_file(
            "- hosts: 123\n" "  tasks:\n" "    - name: T\n" "      bash: echo\n",
            name="playbook.yml",
        )
        with pytest.raises(ValueError, match="must be a non-empty string"):
            parse_playbook(path)

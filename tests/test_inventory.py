from __future__ import annotations

import pytest

from proton_runner.inventory import parse_inventory, resolve_hosts


class TestParseInventory:
    def test_basic_groups(self, tmp_file):
        path = tmp_file(
            "[webservers]\n"
            "foo.example.com\n"
            "bar.example.com\n"
            "\n"
            "[dbservers]\n"
            "one.example.com\n"
            "two.example.com\n",
            name="hosts",
        )
        result = parse_inventory(path)
        assert result == {
            "webservers": ["foo.example.com", "bar.example.com"],
            "dbservers": ["one.example.com", "two.example.com"],
        }

    def test_comments_and_blank_lines(self, tmp_file):
        path = tmp_file(
            "# This is a comment\n"
            "[servers]\n"
            "# Another comment\n"
            "\n"
            "host1.example.com\n"
            "\n"
            "host2.example.com\n",
            name="hosts",
        )
        result = parse_inventory(path)
        assert result == {"servers": ["host1.example.com", "host2.example.com"]}

    def test_duplicate_hosts_deduplicated(self, tmp_file):
        path = tmp_file(
            "[servers]\n"
            "host1.example.com\n"
            "host1.example.com\n"
            "host2.example.com\n",
            name="hosts",
        )
        result = parse_inventory(path)
        assert result == {"servers": ["host1.example.com", "host2.example.com"]}

    def test_whitespace_stripped(self, tmp_file):
        path = tmp_file(
            "[servers]  \n" "  host1.example.com  \n" "host2.example.com\n",
            name="hosts",
        )
        result = parse_inventory(path)
        assert result == {"servers": ["host1.example.com", "host2.example.com"]}

    def test_host_before_group_raises(self, tmp_file):
        path = tmp_file("orphan.example.com\n[servers]\n", name="hosts")
        with pytest.raises(ValueError, match="before any group header"):
            parse_inventory(path)

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found"):
            parse_inventory(tmp_path / "nonexistent")

    def test_empty_file(self, tmp_file):
        path = tmp_file("", name="hosts")
        result = parse_inventory(path)
        assert result == {}

    def test_empty_group(self, tmp_file):
        path = tmp_file("[empty]\n\n[filled]\nhost.com\n", name="hosts")
        result = parse_inventory(path)
        assert result == {"empty": [], "filled": ["host.com"]}

    def test_group_with_hyphens_and_underscores(self, tmp_file):
        path = tmp_file("[my-group_1]\nhost.com\n", name="hosts")
        result = parse_inventory(path)
        assert result == {"my-group_1": ["host.com"]}


class TestResolveHosts:
    def test_existing_group(self):
        inventory = {"web": ["a.com", "b.com"]}
        assert resolve_hosts(inventory, "web") == ["a.com", "b.com"]

    def test_missing_group_raises(self):
        inventory = {"web": ["a.com"], "db": ["b.com"]}
        with pytest.raises(KeyError, match="not found.*Available groups: db, web"):
            resolve_hosts(inventory, "missing")

    def test_missing_group_empty_inventory(self):
        with pytest.raises(KeyError, match="Available groups: \\(none\\)"):
            resolve_hosts({}, "anything")

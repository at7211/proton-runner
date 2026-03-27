from __future__ import annotations

import pytest
from pathlib import Path


@pytest.fixture
def tmp_file(tmp_path: Path):
    """Helper to create a temporary file with given content."""

    def _make(content: str, name: str = "file.txt") -> Path:
        p = tmp_path / name
        p.write_text(content)
        return p

    return _make

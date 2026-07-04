from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "tools"))

import project_scanner


def test_write_output_allows_workspace_paths(tmp_path: Path) -> None:
    out = tmp_path / "scan.json"

    written = project_scanner.write_output(out, '{"schema_version": 1}\n')

    assert Path(written) == out
    assert out.read_text(encoding="utf-8") == '{"schema_version": 1}\n'


def test_write_output_rejects_paths_outside_allowed_roots() -> None:
    out = Path.cwd().parent / "project-scanner-unsafe-out.json"

    with pytest.raises(ValueError, match="Refusing to write outside allowed roots"):
        project_scanner.write_output(out, "{}\n")

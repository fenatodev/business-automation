"""WP-027: synthetic-only private workspace readiness and bootstrap tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from client0_workspace.workspace import (
    TEMPLATE,
    WorkspaceError,
    synthetic_drill,
    workspace_preflight,
)


def make_home(tmp_path: Path) -> Path:
    home = tmp_path / "home"
    home.mkdir(mode=0o700)
    return home


def base(home: Path) -> Path:
    return home / ".local/share/business-automation/client0"


def check_closed(result: dict) -> None:
    assert result["backup_restore_verified"] is False
    assert result["external_action_taken"] is False
    if result["status"] == "ready":
        assert result["publication_authorized"] is False
        assert result["case_contents_inspected"] is False
        assert result["customer_data_collected"] is False
        assert result["backoffice_operational_verified"] is False


def test_preflight_missing_workspace_never_creates_it(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    outcome = workspace_preflight(home=home)
    assert outcome["status"] == "missing"
    check_closed(outcome)
    assert not (home / ".local").exists()


def test_bootstrap_creates_only_private_directories_and_blank_template(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    report = workspace_preflight(home=home, bootstrap_empty=True)
    assert report["status"] == "ready"
    assert report["created"] == [
        ".local", "share", "business-automation", "client0",
        "cases", "templates", "templates/case.md",
    ]
    check_closed(report)
    root = base(home)
    assert {x.name for x in root.iterdir()} == {"cases", "templates"}
    assert list((root / "cases").iterdir()) == []
    assert {x.name for x in (root / "templates").iterdir()} == {"case.md"}
    for folder in [root, root / "cases", root / "templates"]:
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    generated = root / "templates/case.md"
    assert stat.S_IMODE(generated.stat().st_mode) == 0o600
    assert generated.read_bytes() == TEMPLATE.read_bytes()
    assert not (root / "cases/c0-2026-001").exists()


def test_preflight_is_read_only_after_bootstrap(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    workspace_preflight(home=home, bootstrap_empty=True)
    root = base(home)
    marked = root / "cases/placeholder-private.txt"
    marked.write_text("private dummy marker", encoding="utf-8")
    before = marked.stat().st_mtime_ns
    outcome = workspace_preflight(home=home)
    assert outcome["status"] == "ready"
    assert outcome["created"] == []
    assert marked.stat().st_mtime_ns == before
    assert marked.read_text(encoding="utf-8") == "private dummy marker"
    check_closed(outcome)


def test_bootstrap_is_idempotent_and_preserves_unknown_case_data(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    workspace_preflight(home=home, bootstrap_empty=True)
    root = base(home)
    mark = root / "cases/do-not-read-or-touch.txt"
    mark.write_text("synthetic-case-note", encoding="utf-8")
    old = (root / "templates/case.md").read_bytes()
    second = workspace_preflight(home=home, bootstrap_empty=True)
    assert second["status"] == "ready"
    assert second["created"] == []
    assert mark.read_text(encoding="utf-8") == "synthetic-case-note"
    assert (root / "templates/case.md").read_bytes() == old
    check_closed(second)


def test_existing_0600_template_is_never_overwritten(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    workspace_preflight(home=home, bootstrap_empty=True)
    target = base(home) / "templates/case.md"
    custom = b"private existing template version not to be overwritten"
    target.write_bytes(custom)
    outcome = workspace_preflight(home=home, bootstrap_empty=True)
    assert outcome["status"] == "ready"
    assert outcome["created"] == []
    assert target.read_bytes() == custom


@pytest.mark.parametrize("relative", [
    "client0", "client0/cases", "client0/templates",
])
def test_wrong_private_directory_mode_is_rejected(
    tmp_path: Path, relative: str,
) -> None:
    home = make_home(tmp_path)
    workspace_preflight(home=home, bootstrap_empty=True)
    target = home / ".local/share/business-automation" / relative
    target.chmod(0o755)
    with pytest.raises(WorkspaceError, match="private_directory_mode_invalid"):
        workspace_preflight(home=home, bootstrap_empty=True)
    assert stat.S_IMODE(target.stat().st_mode) == 0o755


def test_private_template_wrong_mode_is_rejected_without_chmod(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    workspace_preflight(home=home, bootstrap_empty=True)
    item = base(home) / "templates/case.md"
    item.chmod(0o644)
    with pytest.raises(WorkspaceError, match="private_template_mode_or_type_invalid"):
        workspace_preflight(home=home)
    with pytest.raises(WorkspaceError, match="private_template_mode_or_type_invalid"):
        workspace_preflight(home=home, bootstrap_empty=True)
    assert stat.S_IMODE(item.stat().st_mode) == 0o644


@pytest.mark.parametrize("relative", [
    ".local", ".local/share", ".local/share/business-automation",
    ".local/share/business-automation/client0",
    ".local/share/business-automation/client0/cases",
    ".local/share/business-automation/client0/templates",
])
def test_symlinked_directory_is_rejected(tmp_path: Path, relative: str) -> None:
    home = make_home(tmp_path)
    workspace_preflight(home=home, bootstrap_empty=True)
    subject = home / relative
    external = tmp_path / "external"
    external.mkdir(mode=0o700)
    subject.rename(subject.with_name(subject.name + "-original"))
    subject.symlink_to(external, target_is_directory=True)
    with pytest.raises(WorkspaceError, match="private_directory_unsafe"):
        workspace_preflight(home=home, bootstrap_empty=True)
    assert subject.is_symlink()


def test_template_symlink_never_read_or_followed(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    workspace_preflight(home=home, bootstrap_empty=True)
    path = base(home) / "templates/case.md"
    original = path.read_bytes()
    path.unlink()
    marker = tmp_path / "marker.txt"
    marker.write_text("keep unchanged", encoding="utf-8")
    path.symlink_to(marker)
    with pytest.raises(WorkspaceError, match="private_template_unsafe"):
        workspace_preflight(home=home, bootstrap_empty=True)
    assert marker.read_text(encoding="utf-8") == "keep unchanged"
    assert len(original) > 0


def test_group_writable_parent_cannot_be_auto_corrected(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    parent = home / ".local"
    parent.mkdir(mode=0o700)
    parent.chmod(0o777)
    with pytest.raises(WorkspaceError, match="parent_directory_writable_by_others"):
        workspace_preflight(home=home, bootstrap_empty=True)
    assert stat.S_IMODE(parent.stat().st_mode) == 0o777
    assert not (parent / "share").exists()


def test_private_template_directory_is_not_replaced_by_file(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    workspace_preflight(home=home, bootstrap_empty=True)
    template = base(home) / "templates/case.md"
    template.unlink()
    template.mkdir(mode=0o700)
    with pytest.raises(WorkspaceError, match="private_template_mode_or_type_invalid"):
        workspace_preflight(home=home, bootstrap_empty=True)
    assert template.is_dir()


def test_invalid_public_template_blocks_before_touching_home(tmp_path: Path) -> None:
    home = make_home(tmp_path)
    invalid = tmp_path / "wrong.md"
    invalid.write_text("missing consent markers", encoding="utf-8")
    with pytest.raises(WorkspaceError, match="public_template_invalid"):
        workspace_preflight(home=home, bootstrap_empty=True, template_path=invalid)
    assert not (home / ".local").exists()


def test_preflight_never_reads_public_template_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    home = make_home(tmp_path)
    def no_bytes(_self: Path) -> bytes:
        raise AssertionError("preflight should not inspect public template")
    monkeypatch.setattr(Path, "read_bytes", no_bytes)
    assert workspace_preflight(home=home)["status"] == "missing"


def test_synthetic_drill_exercises_only_temp_home() -> None:
    report = synthetic_drill()
    assert report["kind"] == "client0_synthetic_workspace_drill"
    assert report["status"] == "pass"
    assert report["bootstrap_idempotent"] is True
    assert report["template_sha256_matches"] is True
    assert report["real_workspace_accessed"] is False
    check_closed(report)


def test_synthetic_cli_json_is_sanitized_and_never_accesses_real_home() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "client0_workspace.workspace", "--synthetic-drill"],
        capture_output=True, text=True, check=True,
    )
    status = json.loads(result.stdout)
    assert status["status"] == "pass"
    assert status["backup_restore_verified"] is False
    assert status["external_action_taken"] is False
    assert "case_ref" not in result.stdout
    assert result.stderr == ""


def test_cli_requires_explicit_mode() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "client0_workspace.workspace"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "required" in result.stderr.lower()


def test_code_contains_no_network_database_or_backup_operation() -> None:
    script = (Path(__file__).resolve().parents[1]
              / "client0_workspace/workspace.py").read_text(encoding="utf-8")
    for forbidden in (
        "import httpx", "import requests", "import socket",
        "import psycopg", "import sqlalchemy", "import subprocess",
        "pg_dump(", "pg_restore(", "docker ", "ssh ",
        "publication_authorized\": True",
    ):
        assert forbidden not in script

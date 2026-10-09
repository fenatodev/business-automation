"""WP-030: restic-backed synthetic recovery, never a production backup CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys

import pytest

from client0_workspace.restic_drill import (
    DrillError,
    FILES,
    REQUIRED_RESTIC_COMMANDS,
    _command,
    _generate_fixture,
    _match_bytes,
    synthetic_drill,
)


def _root(tmp_path: Path) -> Path:
    return tmp_path / "source"


def test_synthetic_fixture_contains_exactly_three_invented_files(
    tmp_path: Path,
) -> None:
    root = _root(tmp_path)
    _generate_fixture(root)
    assert _match_bytes(root)
    assert len(FILES) == 3
    assert set(FILES) == {
        "templates/case.md",
        "cases/c0-2099-001/case.md",
        "cases/c0-2099-001/proof-social.json",
    }
    assert all(b"SYN" in v or b"synthetic_only" in v for v in FILES.values())
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert not (root / ".env").exists()


def test_fixture_fails_if_any_content_is_modified(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _generate_fixture(root)
    item = root / "cases/c0-2099-001/case.md"
    item.write_bytes(b"AN UNRELATED SYNTHETIC DOCUMENT\n")
    assert not _match_bytes(root)


def test_fixture_fails_if_unknown_file_is_added(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _generate_fixture(root)
    (root / "cases/c0-2099-001/unexpected.txt").write_text("synthetic")
    assert not _match_bytes(root)


def test_fixture_fails_if_private_file_mode_is_exposed(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _generate_fixture(root)
    item = root / "cases/c0-2099-001/case.md"
    item.chmod(0o644)
    assert not _match_bytes(root)


def test_fixture_does_not_overwrite_any_existing_file(tmp_path: Path) -> None:
    root = _root(tmp_path)
    _generate_fixture(root)
    original = (root / "cases/c0-2099-001/case.md").read_bytes()
    with pytest.raises(FileExistsError):
        _generate_fixture(root)
    assert (root / "cases/c0-2099-001/case.md").read_bytes() == original


def test_whitelisted_restic_argv_is_never_a_shell_script() -> None:
    command = _command(
        "/usr/bin/restic", Path("/tmp/synthetic-only-repo"),
        Path("/tmp/test-only-password"), "check", "--read-data"
    )
    assert command == [
        "/usr/bin/restic", "--repo", "/tmp/synthetic-only-repo",
        "--password-file", "/tmp/test-only-password", "check", "--read-data",
    ]
    assert "shell" not in command
    assert not any(part in command for part in ("--insecure-no-password", "forget", "prune"))
    assert set(REQUIRED_RESTIC_COMMANDS) == {
        "init", "backup", "check", "snapshots", "restore",
    }


@pytest.mark.parametrize("verb", ["forget", "prune", "unlock", "key", "cat", "dump"])
def test_destructive_or_unneeded_restic_commands_are_rejected(verb: str) -> None:
    with pytest.raises(DrillError, match="restic_command_not_allowed"):
        _command("restic", Path("/tmp/repo"), Path("/tmp/pass"), verb)


def test_restic_binary_missing_fails_closed_before_any_input(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(shutil, "which", lambda name: None)
    with pytest.raises(DrillError, match="restic_binary_missing"):
        synthetic_drill()


def test_no_source_repo_password_or_restore_path_can_be_passed_to_cli(
    tmp_path: Path,
) -> None:
    for flags in (("--backup",), ("--restore", "/tmp/real"),
                  ("--source", "/home/private"), ("--repo", "/tmp/other"),
                  ("--password", "invalid")):
        result = subprocess.run(
            [sys.executable, "-m", "client0_workspace.restic_drill", *flags],
            text=True, capture_output=True,
        )
        assert result.returncode == 2
        assert not any(p.is_dir() for p in tmp_path.iterdir())


def test_restic_drill_module_does_not_contain_live_path_or_export_secret() -> None:
    text = (Path(__file__).resolve().parents[1]
            / "client0_workspace/restic_drill.py").read_text(encoding="utf-8")
    for fragment in (
        "Path.home()", "os.environ['HOME']", 'os.environ["HOME"]',
        "RESTIC_PASSWORD=", "shell=True", "restic forget",
        "restic prune", "ssh://", "rest:", "http://", "https://",
        "extractall(", "subprocess.Popen(",
    ):
        assert fragment not in text
    assert "real_backup_restore_verified" in text
    assert "production_backup_authorized" in text
    assert "TemporaryDirectory" in text


@pytest.mark.skipif(shutil.which("restic") is None,
                    reason="Real restic drill runs in separate GitHub Actions job")
def test_actual_restic_encrypts_and_restores_only_synthetic_data() -> None:
    result = synthetic_drill()
    assert result["kind"] == "client0_restic_encrypted_recovery_drill"
    assert result["status"] == "pass"
    assert result["source_classification"] == "synthetic_only"
    assert result["restored_files"] == 3
    assert result["restic_repo_checked_read_data"] is True
    assert result["isolated_restore_verified"] is True
    assert result["synthetic_encrypted_repository_verified"] is True
    assert result["temporary_secret_only"] is True
    assert result["wrong_password_tested"] is True
    for field in (
        "real_workspace_accessed", "real_backup_restore_verified",
        "offsite_backup_verified", "production_backup_authorized",
        "external_action_taken", "customer_data_collected", "site_published",
    ):
        assert result[field] is False


def test_missing_cli_flag_cannot_implicitly_back_up_home() -> None:
    p = subprocess.run(
        [sys.executable, "-m", "client0_workspace.restic_drill"],
        capture_output=True, text=True,
    )
    assert p.returncode == 2
    assert "required" in p.stderr

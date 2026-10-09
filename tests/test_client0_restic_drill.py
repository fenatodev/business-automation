"""WP-030: fail-closed Restic drill; only synthetic temp sources."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

from client0_workspace.restic_drill import (
    ResticDrillError,
    _run_restic,
    main,
    synthetic_drill,
)


def test_unavailable_restic_is_non_destructive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    with pytest.raises(ResticDrillError, match="restic_not_available"):
        synthetic_drill()


def test_cli_requires_synthetic_flag_without_accessing_home() -> None:
    no_args = subprocess.run(
        [sys.executable, "-m", "client0_workspace.restic_drill"],
        capture_output=True, text=True,
    )
    assert no_args.returncode == 2
    for bad in ("--backup", "--restore", "--repository", "--source",
                "--init", "--password", "--apply"):
        request = subprocess.run(
            [sys.executable, "-m", "client0_workspace.restic_drill", bad],
            capture_output=True, text=True,
        )
        assert request.returncode == 2
        assert "unrecognized" in request.stderr or "required" in request.stderr


def test_restic_subcommand_failure_does_not_echo_sensitive_output() -> None:
    sample = "PRIVATE_TEST_STRING_DO_NOT_ECHO"
    command = [sys.executable, "-c",
               f"import sys; print({sample!r}); sys.stderr.write({sample!r}); sys.exit(3)"]
    with pytest.raises(ResticDrillError, match="restic_subcommand_failed") as exc:
        _run_restic(command, env={"PATH": "/usr/bin:/bin"})
    assert sample not in str(exc.value)


def test_restic_subcommand_output_is_bounded() -> None:
    code = "print('x' * 128001)"
    with pytest.raises(ResticDrillError, match="restic_output_excessive"):
        _run_restic(
            [sys.executable, "-c", code],
            env={"PATH": "/usr/bin:/bin"},
        )


def test_restic_subcommand_stderr_excessive_is_rejected() -> None:
    code = "import sys; sys.stderr.write('y' * 128001); sys.exit(0)"
    with pytest.raises(ResticDrillError, match="restic_output_excessive"):
        _run_restic(
            [sys.executable, "-c", code],
            env={"PATH": "/usr/bin:/bin"},
        )


@pytest.mark.skipif(shutil.which("restic") is None,
                    reason="external Restic binary not installed; CI installs it")
def test_real_restic_encrypted_snapshot_and_isolated_restore() -> None:
    data = synthetic_drill()
    assert data == {
        "kind": "client0_restic_encrypted_recovery_drill",
        "status": "pass",
        "backup_engine": "restic",
        "synthetic_file_count": 3,
        "verified_file_count": 3,
        "repository_check_read_data": True,
        "wrong_password_rejected": True,
        "restore_byte_exact": True,
        "restore_isolated": True,
        "repository_encrypted_by_restic": True,
        "real_workspace_accessed": False,
        "real_backup_restore_verified": False,
        "production_repository_created": False,
        "key_recovery_proven": False,
        "external_action_taken": False,
        "publication_authorized": False,
    }


def test_cli_missing_binary_produces_only_sanitized_json(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(shutil, "which", lambda _name: None)
    assert main(["--synthetic-drill"]) == 2
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload == {
        "kind": "client0_restic_encrypted_recovery_drill",
        "status": "blocked",
        "reason": "restic_not_available",
        "real_workspace_accessed": False,
        "real_backup_restore_verified": False,
        "external_action_taken": False,
    }
    assert captured.err == ""


def test_drill_does_not_offer_production_backup_or_restore_entrypoint() -> None:
    source = (Path(__file__).resolve().parents[1]
              / "client0_workspace/restic_drill.py").read_text(encoding="utf-8")
    for excluded in (
        "subprocess.run([\"bash\"", "shell=True", "Path.home()",
        "os.environ.copy()", "restic forget", "restic prune",
        "--backup", "--restore", "--source", "--repository", "rm -rf",
        "RESTIC_PASSWORD=", "subprocess.call(",
    ):
        assert excluded not in source
    assert "secrets.token_urlsafe" in source
    assert "TemporaryDirectory(" in source
    assert "check\", \"--read-data" in source
    assert "wrong_password_rejected" in source
    assert "real_backup_restore_verified" in source

"""WP-028: synthetic-only snapshot/restore with strict integrity and no real HOME."""

from __future__ import annotations

import hashlib
from io import BytesIO
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile, ZipInfo

import pytest

from client0_workspace.recovery import (
    ARCHIVE_NAME,
    RecoveryError,
    _archive_member,
    _read_validated_snapshot,
    _restore_synthetic_snapshot,
    _snapshot_entries,
    _write_synthetic_snapshot,
    synthetic_drill,
)
from client0_workspace.workspace import TEMPLATE


def _write_0600(path: Path, data: bytes) -> None:
    path.write_bytes(data)
    path.chmod(0o600)


def make_fixture(tmp_path: Path, *, case_count: int = 1) -> Path:
    root = tmp_path / "synthetic-source"
    root.mkdir(mode=0o700)
    (root / "cases").mkdir(mode=0o700)
    (root / "templates").mkdir(mode=0o700)
    _write_0600(root / "templates/case.md", TEMPLATE.read_bytes())
    for i in range(case_count):
        folder = root / "cases" / f"c0-2026-{i+1:03d}"
        folder.mkdir(mode=0o700)
        _write_0600(folder / "case.md",
                    f"SYNTHETIC CASE {i+1} - NOT A CUSTOMER\n".encode())
        _write_0600(folder / "proof-social.json",
                    b'{"classification":"unverified","consents":[]}\n')
    return root


def make_archive(tmp_path: Path) -> tuple[Path, Path]:
    src = make_fixture(tmp_path)
    zip_path = tmp_path / ARCHIVE_NAME
    result = _write_synthetic_snapshot(src, zip_path)
    assert result["encrypted"] is False
    assert result["snapshot_files"] == 3
    return src, zip_path


def _rewrite_zip(archive: Path, *, change=None, extra=None) -> None:
    """Rewrite a test-only ZIP, optionally mutating payload or adding member."""
    with ZipFile(archive) as z:
        pairs = [(x, z.read(x.filename)) for x in z.infolist()]
    archive.unlink()
    with ZipFile(archive, "w") as z:
        for old, data in pairs:
            if change is not None:
                data = change(old.filename, data)
            item, payload = _archive_member(old.filename, data)
            z.writestr(item, payload)
        if extra is not None:
            name, body = extra
            item, data = _archive_member(name, body)
            z.writestr(item, data)
    archive.chmod(0o600)


def test_full_synthetic_drill_isolated_and_nonproduction() -> None:
    result = synthetic_drill()
    assert result == {
        "kind": "client0_synthetic_index_recovery",
        "status": "pass",
        "source_classification": "synthetic_only",
        "snapshot_files": 3,
        "restored_files": 3,
        "integrity_sha256_verified": True,
        "restore_isolated": True,
        "archive_encrypted": False,
        "real_workspace_accessed": False,
        "real_backup_restore_verified": False,
        "production_backup_authorized": False,
        "external_action_taken": False,
    }


def test_cli_only_supports_synthetic_drill_and_no_customer_paths() -> None:
    run = subprocess.run(
        [sys.executable, "-m", "client0_workspace.recovery", "--synthetic-drill"],
        capture_output=True, text=True, check=True,
    )
    out = json.loads(run.stdout)
    assert out["status"] == "pass"
    assert out["real_workspace_accessed"] is False
    assert out["production_backup_authorized"] is False
    assert out["archive_encrypted"] is False
    assert "c0-2026-001" not in run.stdout
    assert "SYNTHETIC CASE" not in run.stdout
    assert run.stderr == ""
    no_flags = subprocess.run(
        [sys.executable, "-m", "client0_workspace.recovery"],
        capture_output=True, text=True,
    )
    assert no_flags.returncode == 2
    other_flags = subprocess.run(
        [sys.executable, "-m", "client0_workspace.recovery",
         "--backup", "/home/operator/client0"],
        capture_output=True, text=True,
    )
    assert other_flags.returncode == 2


def test_snapshot_recovery_verifies_same_bytes_and_modes(tmp_path: Path) -> None:
    src, archive = make_archive(tmp_path)
    original = _snapshot_entries(src)
    assert stat.S_IMODE(archive.stat().st_mode) == 0o600
    restored = tmp_path / "restored"
    outcome = _restore_synthetic_snapshot(archive, restored)
    assert outcome == {"status": "pass", "restored_files": 3}
    assert original == _snapshot_entries(restored)
    for folder in (restored, restored / "templates", restored / "cases",
                   restored / "cases/c0-2026-001"):
        assert stat.S_IMODE(folder.stat().st_mode) == 0o700
    for file in (restored / "templates/case.md",
                 restored / "cases/c0-2026-001/case.md",
                 restored / "cases/c0-2026-001/proof-social.json"):
        assert stat.S_IMODE(file.stat().st_mode) == 0o600


def test_snapshot_is_deterministic_and_never_overwrites_file(tmp_path: Path) -> None:
    src, archive = make_archive(tmp_path)
    with pytest.raises(RecoveryError, match="archive_destination_exists"):
        _write_synthetic_snapshot(src, archive)
    second = tmp_path / "second.zip"
    _write_synthetic_snapshot(src, second)
    assert archive.read_bytes() == second.read_bytes()


def test_restore_must_be_new_destination_and_preserves_existing_data(tmp_path: Path) -> None:
    _, archive = make_archive(tmp_path)
    dest = tmp_path / "existing"
    dest.mkdir(mode=0o700)
    marker = dest / "keep.txt"
    _write_0600(marker, b"preserve")
    with pytest.raises(RecoveryError, match="restore_destination_exists"):
        _restore_synthetic_snapshot(archive, dest)
    assert marker.read_bytes() == b"preserve"


def test_restore_destination_symlink_not_followed(tmp_path: Path) -> None:
    _, archive = make_archive(tmp_path)
    real = tmp_path / "real"
    real.mkdir(mode=0o700)
    (tmp_path / "link").symlink_to(real, target_is_directory=True)
    with pytest.raises(RecoveryError, match="restore_destination_exists"):
        _restore_synthetic_snapshot(archive, tmp_path / "link")
    assert list(real.iterdir()) == []


def test_source_symlinked_document_is_not_included(tmp_path: Path) -> None:
    src = make_fixture(tmp_path)
    file = src / "cases/c0-2026-001/case.md"
    file.unlink()
    file.symlink_to(TEMPLATE)
    output = tmp_path / "snapshot.zip"
    with pytest.raises(RecoveryError, match="private_file_unsafe"):
        _write_synthetic_snapshot(src, output)
    assert not output.exists()


@pytest.mark.parametrize("extra", [
    ".env", ".ssh", "tokens.txt", "backup.zip", "private-artifact",
])
def test_unexpected_top_level_file_is_rejected(
    tmp_path: Path, extra: str,
) -> None:
    root = make_fixture(tmp_path)
    _write_0600(root / extra, b"SYN-NOT-ALLOWED")
    with pytest.raises(RecoveryError, match="unknown_root_entry"):
        _snapshot_entries(root)


@pytest.mark.parametrize("name", [
    "contract.pdf", ".env", "document.png", "dump.sql",
])
def test_unreviewed_case_file_is_rejected(tmp_path: Path, name: str) -> None:
    root = make_fixture(tmp_path)
    _write_0600(root / "cases/c0-2026-001" / name, b"dummy")
    with pytest.raises(RecoveryError, match="unknown_or_missing_case_file"):
        _snapshot_entries(root)


def test_bad_case_identifier_rejected(tmp_path: Path) -> None:
    root = make_fixture(tmp_path, case_count=0)
    bad = root / "cases/client-name"
    bad.mkdir(mode=0o700)
    _write_0600(bad / "case.md", b"dummy")
    with pytest.raises(RecoveryError, match="unknown_case_directory"):
        _snapshot_entries(root)


def test_unsafe_source_directory_or_file_mode_fails_without_fix(tmp_path: Path) -> None:
    src = make_fixture(tmp_path)
    path = src / "cases"
    path.chmod(0o755)
    with pytest.raises(RecoveryError, match="private_directory_unsafe"):
        _snapshot_entries(src)
    assert stat.S_IMODE(path.stat().st_mode) == 0o755

    path.chmod(0o700)
    item = src / "cases/c0-2026-001/case.md"
    item.chmod(0o644)
    with pytest.raises(RecoveryError, match="private_file_unsafe"):
        _snapshot_entries(src)
    assert stat.S_IMODE(item.stat().st_mode) == 0o644


def test_manifest_detects_tampered_payload_before_restore(tmp_path: Path) -> None:
    _, archive = make_archive(tmp_path)
    _rewrite_zip(
        archive, change=lambda name, data: (
            data + b"tamp" if name.endswith("case.md") else data
        ),
    )
    target = tmp_path / "restored"
    with pytest.raises(RecoveryError, match="archive_checksum_failed"):
        _restore_synthetic_snapshot(archive, target)
    assert not target.exists()


@pytest.mark.parametrize("path", [
    "../outside.txt", "/etc/issue", "cases/c0-2026-001/../../secret",
    "cases/c0-2026-001/.env", "templates/../../outside",
])
def test_malicious_extra_archive_entries_block_without_extraction(
    tmp_path: Path, path: str,
) -> None:
    _, archive = make_archive(tmp_path)
    _rewrite_zip(archive, extra=(path, b"malicious-fixture"))
    output = tmp_path / "new"
    with pytest.raises(RecoveryError, match="archive_content_mismatch"):
        _restore_synthetic_snapshot(archive, output)
    assert not output.exists()
    assert not (tmp_path / "outside.txt").exists()


def test_archive_duplicate_member_rejected(tmp_path: Path) -> None:
    _, archive = make_archive(tmp_path)
    _rewrite_zip(archive, extra=("cases/c0-2026-001/case.md", b"duplicate"))
    with pytest.raises(RecoveryError, match="archive_members_invalid"):
        _read_validated_snapshot(archive)


def test_archive_without_manifest_rejected(tmp_path: Path) -> None:
    path = tmp_path / "missing.zip"
    with ZipFile(path, "w") as z:
        info, value = _archive_member("cases/c0-2026-001/case.md", b"dummy")
        z.writestr(info, value)
    path.chmod(0o600)
    with pytest.raises(RecoveryError, match="archive_members_invalid"):
        _read_validated_snapshot(path)


def test_archive_symlink_rejected(tmp_path: Path) -> None:
    _, archive = make_archive(tmp_path)
    alias = tmp_path / "alias.zip"
    alias.symlink_to(archive)
    with pytest.raises(RecoveryError):
        _read_validated_snapshot(alias)


def test_compressed_archive_is_not_accepted(tmp_path: Path) -> None:
    path = tmp_path / "compressed.zip"
    with ZipFile(path, "w") as z:
        item = ZipInfo("manifest.json")
        item.compress_type = ZIP_DEFLATED
        item.create_system = 3
        item.external_attr = (stat.S_IFREG | 0o600) << 16
        z.writestr(item, b"{}" * 100)
        item = ZipInfo("templates/case.md")
        item.compress_type = ZIP_DEFLATED
        item.create_system = 3
        item.external_attr = (stat.S_IFREG | 0o600) << 16
        z.writestr(item, b"dummy" * 100)
    path.chmod(0o600)
    with pytest.raises(RecoveryError, match="archive_member_unsafe"):
        _read_validated_snapshot(path)


def test_invalid_archive_fails_closed(tmp_path: Path) -> None:
    archive = tmp_path / "fake.zip"
    _write_0600(archive, b"not a ZIP")
    with pytest.raises(RecoveryError, match="archive_invalid_or_unreadable"):
        _read_validated_snapshot(archive)


def test_private_data_never_enters_report_or_git() -> None:
    text = (Path(__file__).resolve().parents[1]
            / "client0_workspace/recovery.py").read_text(encoding="utf-8")
    for token in (
        "import requests", "import httpx", "import socket", "import psycopg",
        "import sqlalchemy", "import subprocess", "extractall(",
        "urllib.request", "Path.home()", "os.environ[",
    ):
        assert token not in text
    assert "real_backup_restore_verified" in text
    assert "production_backup_authorized" in text

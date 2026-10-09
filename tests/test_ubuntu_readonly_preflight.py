"""WP-031: no-live-data tests of metadata-only host inventory."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import subprocess
import sys

import pytest

from scripts.ubuntu_readonly_preflight import (
    _mount_entry_present,
    _private_workspace,
    _state,
    collect,
)


def _home(tmp: Path) -> Path:
    home = tmp / "fake-home"
    home.mkdir(mode=0o700)
    return home


def _safe_layout(home: Path) -> Path:
    base = home
    for name, mode in (
        (".local", 0o700), ("share", 0o700),
        ("business-automation", 0o700), ("client0", 0o700),
    ):
        base = base / name
        base.mkdir(mode=mode)
    (base / "cases").mkdir(mode=0o700)
    (base / "templates").mkdir(mode=0o700)
    sample = base / "templates/case.md"
    sample.write_text("synthetic-private-fixture")
    sample.chmod(0o600)
    return base


def _mount(tmp: Path) -> Path:
    path = tmp / "fake-mount"
    path.mkdir(mode=0o700)
    return path


def _mount_line(path: Path) -> str:
    return f"20 19 8:1 / {path} rw,relatime - ext4 /dev/fake rw\n"


def test_missing_private_workspace_reports_no_data_reads(tmp_path: Path) -> None:
    home = _home(tmp_path)
    report = collect(
        home=home, backup_candidate=_mount(tmp_path),
        mountinfo="", which=lambda _tool: None,
    )
    assert report["kind"] == "client0_ubuntu_readonly_preflight"
    assert report["status"] == "review_required"
    assert report["workspace_metadata"][".local"] == "missing"
    assert report["workspace_metadata"]["cases"] == "not_checked"
    assert report["backup_storage"]["mount_detected"] is False
    assert report["tools_available"] == {
        "restic": False, "git": False, "uv": False, "opencode": False
    }
    for flag in ("private_case_contents_read", "database_accessed",
                 "backup_executed", "restore_executed",
                 "user_files_modified", "software_installed",
                 "network_scanned", "mxq4k_accessed",
                 "publication_authorized"):
        assert report[flag] is False


def test_existing_workspace_uses_only_metadata(tmp_path: Path) -> None:
    home = _home(tmp_path)
    base = _safe_layout(home)
    customer_marker = base / "cases/do-not-open-private.txt"
    customer_marker.write_text("private payload must not be read")
    before = customer_marker.stat().st_mtime_ns
    result = collect(
        home=home, backup_candidate=_mount(tmp_path), mountinfo="",
        which=lambda x: "/bin/yes" if x == "restic" else None,
    )
    assert set(result["workspace_metadata"].values()) == {"safe"}
    assert result["tools_available"]["restic"] is True
    assert customer_marker.stat().st_mtime_ns == before
    assert customer_marker.read_text() == "private payload must not be read"
    assert result["user_files_modified"] is False
    assert result["private_case_contents_read"] is False


@pytest.mark.parametrize("part", [
    ".local", ".local/share", ".local/share/business-automation",
    ".local/share/business-automation/client0",
    ".local/share/business-automation/client0/cases",
    ".local/share/business-automation/client0/templates",
])
def test_symlink_component_blocks_without_following(tmp_path: Path, part: str) -> None:
    home = _home(tmp_path)
    _safe_layout(home)
    target = home / part
    backup = target.with_name(target.name + "-original")
    target.rename(backup)
    target.symlink_to(backup, target_is_directory=True)
    probe = _private_workspace(home)
    assert "blocked" in probe.values()


@pytest.mark.parametrize("mode", [0o755, 0o770, 0o777])
def test_unsafe_private_directory_permissions_are_blocked(
    tmp_path: Path, mode: int
) -> None:
    home = _home(tmp_path)
    base = _safe_layout(home)
    base.chmod(mode)
    report = _private_workspace(home)
    assert report["client0"] == "blocked"
    assert report["cases"] == "not_checked"
    assert stat.S_IMODE(base.stat().st_mode) == mode


def test_unsafe_template_metadata_does_not_open_file(tmp_path: Path) -> None:
    home = _home(tmp_path)
    base = _safe_layout(home)
    template = base / "templates/case.md"
    template.chmod(0o644)
    report = _private_workspace(home)
    assert report["template_file"] == "blocked"
    assert stat.S_IMODE(template.stat().st_mode) == 0o644


def test_mount_candidate_path_is_not_equivalent_to_real_mount(tmp_path: Path) -> None:
    home = _home(tmp_path)
    candidate = _mount(tmp_path)
    report = collect(
        home=home, backup_candidate=candidate,
        mountinfo="", which=lambda _: None,
    )
    assert report["backup_storage"]["directory_status"] == "safe"
    assert report["backup_storage"]["mount_detected"] is False
    assert report["backup_storage"]["physical_independence_verified"] is False
    assert report["backup_storage"]["backup_write_test_performed"] is False


def test_detect_mountpoint_but_never_prove_physical_independence(tmp_path: Path) -> None:
    home = _home(tmp_path)
    candidate = _mount(tmp_path)
    report = collect(
        home=home, backup_candidate=candidate,
        mountinfo=_mount_line(candidate), which=lambda _: None,
    )
    storage = report["backup_storage"]
    assert storage["mount_detected"] is True
    assert storage["distinct_filesystem_from_home"] is False
    assert storage["physical_independence_verified"] is False
    assert storage["backup_write_test_performed"] is False


def test_mountinfo_must_match_exact_path(tmp_path: Path) -> None:
    path = _mount(tmp_path)
    info = _mount_line(path.with_name(path.name + "-else"))
    assert _mount_entry_present(path, info) is False
    assert _mount_entry_present(path, _mount_line(path)) is True


def test_backup_mount_symlink_is_blocked(tmp_path: Path) -> None:
    home = _home(tmp_path)
    path = _mount(tmp_path)
    alias = tmp_path / "alias"
    alias.symlink_to(path, target_is_directory=True)
    report = collect(
        home=home, backup_candidate=alias,
        mountinfo=_mount_line(alias), which=lambda _: None,
    )
    assert report["status"] == "blocked"
    assert report["backup_storage"]["mount_detected"] is False
    assert alias.is_symlink()


def test_public_mount_can_be_owned_by_different_user(tmp_path: Path,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    path = _mount(tmp_path)
    # Flag distinguishes workspace owner requirement from mount ownership.
    assert _state(path, owned=False) == "safe"


def test_cli_does_not_accept_backup_install_or_deploy_parameters() -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/ubuntu_readonly_preflight.py"
    for argument in ("--backup", "--restore", "--install", "--deploy",
                     "--path", "--home", "--sudo", "--mxq"):
        p = subprocess.run(
            [sys.executable, "-B", str(script), argument],
            capture_output=True, text=True,
        )
        assert p.returncode == 2
        assert "required" in p.stderr or "unrecognized" in p.stderr


def test_inventory_code_contains_no_write_network_or_shell_actions() -> None:
    code = (Path(__file__).resolve().parents[1]
            / "scripts/ubuntu_readonly_preflight.py").read_text()
    for forbidden in (
        "subprocess.", "socket.", ".write_text(", ".write_bytes(",
        "os.remove(", "os.mkdir(", "open(", "os.system(", "Path.home() /",
        "restic init", "restic backup", "chmod(", "shutil.rmtree(",
    ):
        assert forbidden not in code
    assert 'Path("/proc/self/mountinfo").read_text' in code
    assert '"user_files_modified": False' in code

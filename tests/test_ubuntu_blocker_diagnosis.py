"""WP-032: synthetic-only unit coverage, no host inventory in CI."""

from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.ubuntu_blocker_diagnosis import (
    KIND,
    collect,
    disk_topology,
    inspect_workspace_blocker,
)


def _fake_home(tmp_path: Path) -> tuple[Path, Path]:
    home = tmp_path / "fake-home"
    target = home / ".local/share/business-automation"
    target.mkdir(parents=True, mode=0o700)
    target.chmod(0o700)
    return home, target


def _disk_sample(
    *, backup_disk: str = "sdb",
    duplicate_root: bool = False,
    complex_backup: bool = False,
) -> dict:
    partitions = [{
        "name": "sda5", "type": "part",
        "mountpoints": ["/"], "children": [],
    }]
    if backup_disk == "sda":
        partitions.append({
            "name": "sda6", "type": "part",
            "mountpoints": ["/mnt/backup"], "children": [],
        })
    devices = [{
        "name": "sda", "type": "disk",
        "mountpoints": [None], "children": partitions,
    }]
    if backup_disk != "sda":
        target = {
            "name": "sdb1",
            "type": "crypt" if complex_backup else "part",
            "mountpoints": ["/mnt/backup"], "children": [],
        }
        devices.append({
            "name": "sdb", "type": "disk",
            "mountpoints": [None], "children": [target],
        })
    if duplicate_root:
        devices.append({
            "name": "nvme0n1", "type": "disk", "mountpoints": [None],
            "children": [{"name": "nvme0n1p1", "type": "part",
                          "mountpoints": ["/"]}],
        })
    return {"blockdevices": devices}


def test_private_0700_directory_is_safe(tmp_path: Path) -> None:
    home, target = _fake_home(tmp_path)
    r = inspect_workspace_blocker(home, uid=target.stat().st_uid)
    assert r == {
        "state": "safe", "mode": "0700", "owned_by_current_user": True
    }


@pytest.mark.parametrize("mode", [0o755, 0o750, 0o770, 0o777, 0o500])
def test_private_mode_mismatch_reports_exact_mode(
    tmp_path: Path, mode: int
) -> None:
    home, target = _fake_home(tmp_path)
    target.chmod(mode)
    r = inspect_workspace_blocker(home, uid=target.stat().st_uid)
    assert r["state"] == "private_mode_mismatch"
    assert r["mode"] == format(mode, "04o")
    assert r["owned_by_current_user"] is True
    # Diagnosis must not repair the permissions itself.
    assert target.stat().st_mode & 0o777 == mode


def test_private_directory_wrong_owner(tmp_path: Path) -> None:
    home, target = _fake_home(tmp_path)
    r = inspect_workspace_blocker(home, uid=target.stat().st_uid + 1000)
    assert r["state"] == "different_owner"
    assert r["owned_by_current_user"] is False


def test_symlink_not_followed(tmp_path: Path) -> None:
    home, target = _fake_home(tmp_path)
    other = target.with_name("untouched-target")
    target.rename(other)
    target.symlink_to(other, target_is_directory=True)
    r = inspect_workspace_blocker(home, uid=other.stat().st_uid)
    assert r["state"] == "symlink"
    assert other.is_dir()


def test_missing_path(tmp_path: Path) -> None:
    home = tmp_path / "fake-home"
    home.mkdir()
    assert inspect_workspace_blocker(home, uid=123)["state"] == "missing"


def test_file_instead_of_directory(tmp_path: Path) -> None:
    home, target = _fake_home(tmp_path)
    target.rmdir()
    target.write_text("synthetic", encoding="utf-8")
    r = inspect_workspace_blocker(home, uid=target.stat().st_uid)
    assert r["state"] == "not_directory"
    assert target.read_text(encoding="utf-8") == "synthetic"


def test_different_disks_not_claimed_physically_independent() -> None:
    v = disk_topology(_disk_sample(), home="/home/example")
    assert v == {
        "topology": "different_block_disks",
        "different_block_disks": True,
        "physical_independence_verified": False,
    }


def test_same_disk_different_partitions_still_not_independent() -> None:
    v = disk_topology(_disk_sample(backup_disk="sda"), home="/home/example")
    assert v["topology"] == "same_block_disk"
    assert v["different_block_disks"] is False
    assert v["physical_independence_verified"] is False


@pytest.mark.parametrize("devices", [
    {"blockdevices": []},
    {"blockdevices": "invalid"},
    {"other": True},
    _disk_sample(duplicate_root=True),
    _disk_sample(complex_backup=True),
])
def test_missing_or_ambiguous_block_graph_returns_unknown(devices: dict) -> None:
    v = disk_topology(devices, home="/home/example")
    assert v["topology"] == "indeterminate"
    assert v["different_block_disks"] is None


def test_workspace_subdirectory_mount_takes_precedence() -> None:
    devices = _disk_sample()
    devices["blockdevices"][0]["children"].append({
        "name": "sda8", "type": "part",
        "mountpoints": ["/home"], "children": [],
    })
    r = disk_topology(devices, home="/home/example")
    assert r["topology"] == "different_block_disks"


def test_synthetic_report_never_claims_real_operational_changes(
    tmp_path: Path,
) -> None:
    home, target = _fake_home(tmp_path)
    target.chmod(0o755)
    r = collect(home=home, uid=target.stat().st_uid, devices=_disk_sample())
    assert r["kind"] == KIND == "client0_ubuntu_blocker_diagnosis"
    assert r["status"] == "needs_human_review"
    assert r["workspace_blocker"]["state"] == "private_mode_mismatch"
    assert r["backup_disk_topology"]["physical_independence_verified"] is False
    for flag in ("restic_installation_authorized", "permission_change_authorized",
                 "real_backup_restore_verified", "case_contents_inspected",
                 "private_files_modified", "software_installed",
                 "backup_executed", "restore_executed", "external_action_taken"):
        assert r[flag] is False
    # The JSON omits raw device names, source paths, uid and private contents.
    encoded = json.dumps(r)
    assert "sdb" not in encoded
    assert str(home) not in encoded
    assert "st_uid" not in encoded


@pytest.mark.parametrize("argument", [
    "--backup", "--restore", "--install", "--fix", "--chmod",
    "--write", "--sudo", "--devices", "--mount", "--deploy",
])
def test_cli_rejects_unauthorized_modes(argument: str) -> None:
    script = Path(__file__).resolve().parents[1] / "scripts/ubuntu_blocker_diagnosis.py"
    completed = subprocess.run(
        [sys.executable, "-B", str(script), argument],
        check=False, capture_output=True, text=True,
    )
    assert completed.returncode == 2
    assert "required" in completed.stderr or "unrecognized" in completed.stderr


def test_script_never_offers_prod_backup_entrypoint() -> None:
    text = (
        Path(__file__).resolve().parents[1]
        / "scripts/ubuntu_blocker_diagnosis.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "shell=True", "os.system(", "os.chmod(", ".chmod(", "os.mkdir(",
        ".mkdir(", ".write_text(", ".write_bytes(", "os.remove(",
        "restic init", "restic backup", "shutil.rmtree(",
        "subprocess.Popen", "sudo", "mount -",
    ):
        assert forbidden not in text

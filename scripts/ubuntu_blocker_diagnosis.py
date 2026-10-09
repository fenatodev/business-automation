"""WP-032: diagnose the existing Ubuntu WP-031 blocker, read-only.

Reads lstat metadata for ONE fixed directory and queries block topology
using unprivileged lsblk. Does not enumerate HOME, read case contents,
modify permissions, mount devices, install packages or run backups.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
from typing import Any


KIND = "client0_ubuntu_blocker_diagnosis"
BLOCK_PATH = ".local/share/business-automation"
BACKUP_MOUNT = "/mnt/backup"


def inspect_workspace_blocker(home: Path, *, uid: int) -> dict[str, Any]:
    """Inspect only the fixed blocked node; never list its children."""
    candidate = home / BLOCK_PATH
    try:
        info = candidate.lstat()
    except FileNotFoundError:
        return {"state": "missing", "mode": None, "owned_by_current_user": None}
    except OSError:
        return {"state": "inaccessible", "mode": None, "owned_by_current_user": None}

    mode = stat.S_IMODE(info.st_mode)
    owner_match = info.st_uid == uid
    if stat.S_ISLNK(info.st_mode):
        state = "symlink"
    elif not stat.S_ISDIR(info.st_mode):
        state = "not_directory"
    elif not owner_match:
        state = "different_owner"
    elif mode != 0o700:
        state = "private_mode_mismatch"
    else:
        state = "safe"

    return {
        "state": state,
        "mode": format(mode, "04o"),
        "owned_by_current_user": owner_match,
    }


def disk_topology(
    payload: dict[str, Any], *, home: str, backup: str = BACKUP_MOUNT
) -> dict[str, Any]:
    """Report only whether simple disk->partition mount ancestry differs.

    Device names and mount sources are never surfaced; complex or ambiguous
    stacks (LVM, RAID, device mapper, network mounts) remain indeterminate.
    """
    entries: list[tuple[str, str, bool, str | None]] = []

    def descend(node: Any, parent: str | None, simple: bool) -> None:
        if not isinstance(node, dict):
            return
        kind = node.get("type")
        name = node.get("name")
        if not isinstance(kind, str) or not isinstance(name, str):
            return
        disk = name if kind == "disk" else parent
        simple_here = (kind == "disk") or (simple and kind == "part")
        mounts = node.get("mountpoints")
        if not isinstance(mounts, list):
            mounts = []
        for mounted in mounts:
            if isinstance(mounted, str) and mounted.startswith("/"):
                entries.append((mounted, disk or "", simple_here, kind))
        children = node.get("children")
        if isinstance(children, list):
            for child in children:
                descend(child, disk, simple_here)

    nodes = payload.get("blockdevices") if isinstance(payload, dict) else None
    if not isinstance(nodes, list):
        return {"topology": "indeterminate", "different_block_disks": None,
                "physical_independence_verified": False}
    for node in nodes:
        descend(node, None, False)

    # HOME might be part of '/' or on its own mounted volume.
    matches = [
        entry for entry in entries
        if home == entry[0] or home.startswith(entry[0].rstrip("/") + "/")
        or entry[0] == "/"
    ]
    if matches:
        longest = max(len(e[0]) for e in matches)
        matches = [e for e in matches if len(e[0]) == longest]
    backup_matches = [e for e in entries if e[0] == backup]

    if (
        len(matches) != 1 or len(backup_matches) != 1
        or not matches[0][2] or not backup_matches[0][2]
        or not matches[0][1] or not backup_matches[0][1]
    ):
        state, differs = "indeterminate", None
    else:
        differs = matches[0][1] != backup_matches[0][1]
        state = "different_block_disks" if differs else "same_block_disk"
    return {
        "topology": state,
        "different_block_disks": differs,
        # Different disk nodes != proof of independent physical media.
        "physical_independence_verified": False,
    }


def _get_lsblk_json() -> dict[str, Any] | None:
    binary = shutil.which("lsblk")
    if binary is None:
        return None
    try:
        result = subprocess.run(
            [binary, "--json", "--output", "NAME,TYPE,MOUNTPOINTS"],
            capture_output=True, text=True, check=False, timeout=8,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode or len(result.stdout) > 256_000:
        return None
    try:
        value = json.loads(result.stdout)
    except ValueError:
        return None
    return value if isinstance(value, dict) else None


def collect(*, home: Path, uid: int, devices: dict[str, Any] | None) -> dict[str, Any]:
    workspace = inspect_workspace_blocker(home, uid=uid)
    topology = disk_topology(devices, home=str(home)) if devices is not None else {
        "topology": "indeterminate",
        "different_block_disks": None,
        "physical_independence_verified": False,
    }
    return {
        "kind": KIND,
        "status": "needs_human_review",
        "wp031_previous_status": "blocked_unresolved",
        "workspace_blocker": workspace,
        "backup_disk_topology": topology,
        "restic_installation_authorized": False,
        "permission_change_authorized": False,
        "real_backup_restore_verified": False,
        "case_contents_inspected": False,
        "private_files_modified": False,
        "software_installed": False,
        "backup_executed": False,
        "restore_executed": False,
        "external_action_taken": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP-032: read-only blocker diagnosis")
    parser.add_argument("--check", required=True, action="store_true")
    parser.parse_args(argv)
    result = collect(home=Path.home(), uid=os.geteuid(), devices=_get_lsblk_json())
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""WP-031: read-only, sanitized Ubuntu readiness inventory.

No application or database access. No file content under HOME is opened.
No backup, install, network probes, service starts or user-data writes.
Only fixed path metadata, /proc/self/mountinfo and command availability.
Call: python3 -B scripts/ubuntu_readonly_preflight.py --check
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import shutil
import stat
from typing import Callable


TOOLS = ("restic", "git", "uv", "opencode")


def _state(
    path: Path, *, kind: str = "dir", private: bool = False, owned: bool = True
) -> str:
    """Inode metadata only: never read filenames or contents."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "blocked"
    if (stat.S_ISLNK(info.st_mode) or (owned and info.st_uid != os.geteuid())
            or (kind == "dir" and not stat.S_ISDIR(info.st_mode))
            or (kind == "file" and not stat.S_ISREG(info.st_mode))):
        return "blocked"
    mode = stat.S_IMODE(info.st_mode)
    if private:
        if mode != (0o700 if kind == "dir" else 0o600):
            return "blocked"
    elif mode & 0o022:
        return "blocked"
    return "safe"


def _private_workspace(home: Path) -> dict[str, str]:
    """Inspect fixed components and sibling directories; no enumeration."""
    paths = [
        ("home", home, False, "dir"),
        (".local", home / ".local", False, "dir"),
        ("share", home / ".local/share", False, "dir"),
        ("business-automation", home / ".local/share/business-automation", True, "dir"),
        ("client0", home / ".local/share/business-automation/client0", True, "dir"),
    ]
    result: dict[str, str] = {}
    root_safe = True
    for name, path, private, kind in paths:
        status = _state(path, private=private, kind=kind) if root_safe else "not_checked"
        result[name] = status
        if status != "safe":
            root_safe = False
    base = home / ".local/share/business-automation/client0"
    for name, path, kind in (
        ("cases", base / "cases", "dir"),
        ("templates", base / "templates", "dir"),
        ("template_file", base / "templates/case.md", "file"),
    ):
        parent_name = "client0" if name in ("cases", "templates") else "templates"
        parent_ok = result[parent_name] == "safe"
        result[name] = _state(path, private=True, kind=kind) if parent_ok else "not_checked"
    return result


def _mount_entry_present(path: Path, mountinfo: str) -> bool:
    """Check exact mountpoint; a directory alone is not a mounted volume."""
    expected = str(path)
    for line in mountinfo.splitlines():
        left = line.partition(" - ")[0].split()
        if len(left) >= 5:
            decoded = (
                left[4].replace("\\040", " ").replace("\\011", "\t")
                .replace("\\012", "\n").replace("\\134", "\\")
            )
            if decoded == expected:
                return True
    return False


def _backup_mount(home: Path, candidate: Path, mountinfo: str) -> dict[str, object]:
    # A symlinked parent or candidate is never followed.
    if _state(candidate.parent, owned=False) != "safe":
        state = "blocked"
    else:
        state = _state(candidate, owned=False)
    mounted = state == "safe" and _mount_entry_present(candidate, mountinfo)
    distinct: bool | None = None
    if mounted and _state(home) == "safe":
        try:
            distinct = home.stat().st_dev != candidate.stat().st_dev
        except OSError:
            pass
    return {
        "directory_status": state,
        "mount_detected": bool(mounted),
        "distinct_filesystem_from_home": distinct,
        "physical_independence_verified": False,
        "backup_write_test_performed": False,
    }


def collect(
    *, home: Path, backup_candidate: Path, mountinfo: str,
    which: Callable[[str], str | None] = shutil.which,
) -> dict[str, object]:
    workspace = _private_workspace(home)
    blocked = any(item == "blocked" for item in workspace.values())
    storage = _backup_mount(home, backup_candidate, mountinfo)
    return {
        "kind": "client0_ubuntu_readonly_preflight",
        "status": "blocked" if blocked or storage["directory_status"] == "blocked"
                  else "review_required",
        "host_architecture": platform.machine(),
        "workspace_metadata": workspace,
        "tools_available": {tool: bool(which(tool)) for tool in TOOLS},
        "backup_storage": storage,
        "private_case_contents_read": False,
        "database_accessed": False,
        "backup_executed": False,
        "restore_executed": False,
        "user_files_modified": False,
        "software_installed": False,
        "network_scanned": False,
        "mxq4k_accessed": False,
        "publication_authorized": False,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only operational inventory; never backup or deploy."
    )
    parser.add_argument("--check", action="store_true", required=True)
    parser.parse_args(argv)
    try:
        mountinfo = Path("/proc/self/mountinfo").read_text(encoding="utf-8")
    except OSError:
        mountinfo = ""
    result = collect(
        home=Path.home(),
        backup_candidate=Path("/mnt/backup"),
        mountinfo=mountinfo,
    )
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] == "blocked" else 0


if __name__ == "__main__":
    raise SystemExit(main())

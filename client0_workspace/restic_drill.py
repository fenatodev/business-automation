"""WP-030: end-to-end Restic encrypted recovery using ONLY invented temp files.

There is intentionally NO production backup, restore, repository or path CLI.
Do not attach any snapshot artifact to CI, expose a source path or print secrets.
Restic is a mature external program; this harness does not implement crypto.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import shutil
import stat
import subprocess
import sys
from tempfile import TemporaryDirectory
from typing import Any


class ResticDrillError(RuntimeError):
    """Only fixed error codes are printed; never leak command output."""


def _make_private_dir(path: Path) -> None:
    path.mkdir(mode=0o700)
    if stat.S_IMODE(path.stat().st_mode) != 0o700:
        raise ResticDrillError("temporary_directory_unsafe")


def _write_private(path: Path, body: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(body)


def _run_restic(command: list[str], *, env: dict[str, str]) -> str:
    """Capture ALL output, do not print paths, passwords, or file metadata."""
    try:
        finished = subprocess.run(
            command,
            env=env,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise ResticDrillError("restic_execution_failed") from exc
    if finished.returncode != 0:
        raise ResticDrillError("restic_subcommand_failed")
    if len(finished.stdout) > 128_000:
        raise ResticDrillError("restic_output_excessive")
    if len(finished.stderr) > 128_000:
        raise ResticDrillError("restic_output_excessive")
    return finished.stdout


def synthetic_drill(*, executable: str = "restic") -> dict[str, Any]:
    """No reads/writes under real HOME or live business files."""
    binary = shutil.which(executable)
    if binary is None:
        raise ResticDrillError("restic_not_available")

    with TemporaryDirectory(prefix="ba-wp030-synthetic-") as parent:
        work = Path(parent)
        work.chmod(0o700)
        home = work / "fake-home"
        cache = work / "cache"
        source = work / "synthetic-source"
        repo = work / "encrypted-repository"
        restored = work / "isolated-restore"
        for path in (home, cache, source):
            _make_private_dir(path)

        paths = (
            "templates/case.md",
            "cases/c0-2026-001/case.md",
            "cases/c0-2026-001/proof-social.json",
        )
        payloads = {
            "templates/case.md": b"# SYN-UNAPPROVED-TEMPLATE\n",
            "cases/c0-2026-001/case.md":
                b"SYN-CASE-001\nSYN-OPP-001\nSYN-QUOTE-V1\n",
            "cases/c0-2026-001/proof-social.json":
                b'{"classification":"synthetic_only","consents":[]}\n',
        }
        for folder in (
            source / "templates",
            source / "cases",
            source / "cases" / "c0-2026-001",
        ):
            _make_private_dir(folder)
        for name in paths:
            _write_private(source / name, payloads[name])

        password_path = work / "synthetic-password"
        wrong_password_path = work / "wrong-password"
        _write_private(
            password_path, (secrets.token_urlsafe(48) + "\n").encode("ascii")
        )
        _write_private(
            wrong_password_path, (secrets.token_urlsafe(48) + "\n").encode("ascii")
        )

        # Do not pass the caller's environment, credentials, HOME or Restic
        # configuration to the subprocess. This prevents accidental external
        # repository selection from RESTIC_* variables.
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(home),
            "XDG_CACHE_HOME": str(cache),
            "LANG": "C",
        }
        base = [binary, "--repo", str(repo), "--password-file",
                str(password_path)]
        _run_restic([*base, "init"], env=env)
        _run_restic([*base, "backup", "--one-file-system", str(source)],
                    env=env)

        snapshots_json = _run_restic([*base, "snapshots", "--json"], env=env)
        try:
            snapshots = json.loads(snapshots_json)
        except ValueError as exc:
            raise ResticDrillError("invalid_restic_snapshot_json") from exc
        if (
            not isinstance(snapshots, list)
            or len(snapshots) != 1
            or snapshots[0].get("paths") != [str(source)]
        ):
            raise ResticDrillError("synthetic_snapshot_scope_invalid")
        snapshot_id = snapshots[0].get("id")
        if (
            not isinstance(snapshot_id, str) or len(snapshot_id) != 64
            or any(c not in "0123456789abcdef" for c in snapshot_id)
        ):
            raise ResticDrillError("synthetic_snapshot_id_invalid")

        _run_restic([*base, "check", "--read-data"], env=env)

        # An incorrect password must fail. This is not a user login test.
        denied = subprocess.run(
            [binary, "--repo", str(repo), "--password-file",
             str(wrong_password_path), "snapshots", "--json"],
            env=env, capture_output=True, text=True, timeout=120,
            check=False,
        )
        if denied.returncode == 0:
            raise ResticDrillError("wrong_password_not_rejected")

        if restored.exists() or restored.is_symlink():
            raise ResticDrillError("restore_destination_already_exists")
        _run_restic(
            [*base, "restore", snapshot_id, "--target", str(restored)],
            env=env,
        )
        # Restic restores absolute paths under target, never to the
        # original source. Verify all recovered files byte-for-byte.
        recovery_root = restored / source.relative_to("/")
        if not recovery_root.is_dir():
            raise ResticDrillError("restore_root_missing")
        for name in paths:
            item = recovery_root / name
            if (
                not item.is_file()
                or item.is_symlink()
                or item.read_bytes() != payloads[name]
                or stat.S_IMODE(item.stat().st_mode) != 0o600
            ):
                raise ResticDrillError("restore_bytes_or_mode_mismatch")

        if (
            {x.name for x in recovery_root.iterdir()}
            != {"cases", "templates"}
            or {x.name for x in (recovery_root / "cases").iterdir()}
            != {"c0-2026-001"}
        ):
            raise ResticDrillError("restore_scope_unexpected")

        return {
            "kind": "client0_restic_encrypted_recovery_drill",
            "status": "pass",
            "backup_engine": "restic",
            "synthetic_file_count": len(paths),
            "verified_file_count": len(paths),
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="WP-030: encrypted restic test against synthetic files ONLY."
    )
    parser.add_argument("--synthetic-drill", action="store_true", required=True)
    parser.parse_args(argv)
    try:
        report = synthetic_drill()
    except ResticDrillError as exc:
        print(json.dumps({
            "kind": "client0_restic_encrypted_recovery_drill",
            "status": "blocked",
            "reason": str(exc),
            "real_workspace_accessed": False,
            "real_backup_restore_verified": False,
            "external_action_taken": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

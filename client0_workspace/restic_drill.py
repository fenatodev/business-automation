"""WP-030: prove restic encryption and isolated restore with invented data only.

There is deliberately NO CLI for backup, source, restore, repository,
password, arbitrary paths, retention or destruction. No production data
or credentials can be passed in. The only mode creates every input inside
one OS-managed disposable directory and uses the installed restic binary.
This is a DRILL, not a real backup setup.
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


TAG = "wp030-synthetic-only"
# Intentionally harmless invented text; no identifiers of real customers.
FILES: dict[str, bytes] = {
    "templates/case.md": b"# SYNTHETIC TEMPLATE WP030 - NOT A CUSTOMER\n",
    "cases/c0-2099-001/case.md": (
        b"# SYNTHETIC CASE WP030 - NOT A REAL CONTRACT OR PAYMENT\n"
        b"SYN-OPP-2099-001\nSYN-QUOTE-V1\n"
    ),
    "cases/c0-2099-001/proof-social.json": (
        b'{"classification":"synthetic_only","consent":[],"publish":false}\n'
    ),
}
REQUIRED_RESTIC_COMMANDS = ("init", "backup", "check", "snapshots", "restore")


class DrillError(RuntimeError):
    """Fixed, non-sensitive error codes; subprocess output is never exposed."""


def _private_write(path: Path, payload: bytes) -> None:
    """Create one synthetic file, no existing file overwrite."""
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(payload)


def _generate_fixture(root: Path) -> None:
    """Root is a newly created disposable directory controlled by the drill."""
    root.mkdir(mode=0o700)
    for dirname in ("templates", "cases", "cases/c0-2099-001"):
        (root / dirname).mkdir(mode=0o700)
    for relative, content in FILES.items():
        _private_write(root / relative, content)


def _command(
    binary: str, repository: Path, password_file: Path, verb: str, *arguments: str
) -> list[str]:
    if verb not in REQUIRED_RESTIC_COMMANDS:
        raise DrillError("restic_command_not_allowed")
    return [
        binary, "--repo", str(repository), "--password-file", str(password_file),
        verb, *arguments,
    ]


def _invoke(
    binary: str, repo: Path, password_file: Path, verb: str,
    *args: str, cwd: Path, environment: dict[str, str],
) -> str:
    try:
        run = subprocess.run(
            _command(binary, repo, password_file, verb, *args),
            cwd=cwd,
            env=environment,
            check=False,
            text=True,
            capture_output=True,
            timeout=90,
        )
    except (OSError, subprocess.TimeoutExpired, UnicodeError) as exc:
        raise DrillError(f"restic_{verb}_unavailable") from exc
    if run.returncode:
        raise DrillError(f"restic_{verb}_failed")
    return run.stdout


def _match_bytes(root: Path) -> bool:
    """Compare against hardcoded fictitious fixture; no reading other folders."""
    names: set[str] = set()
    for dirname in ("templates", "cases", "cases/c0-2099-001"):
        target = root / dirname
        info = target.lstat()
        if (not stat.S_ISDIR(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o700):
            return False
    for relative, expected in FILES.items():
        target = root / relative
        info = target.lstat()
        if (not stat.S_ISREG(info.st_mode)
                or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_size != len(expected)):
            return False
        actual = target.read_bytes()
        if hashlib.sha256(actual).digest() != hashlib.sha256(expected).digest():
            return False
        names.add(relative)
    present = {
        p.relative_to(root).as_posix() for p in root.rglob("*") if p.is_file()
    }
    return present == names


def synthetic_drill(*, binary: str | None = None) -> dict[str, Any]:
    """Use restic in a private temporary sandbox; never touch the live HOME."""
    executable = binary or shutil.which("restic")
    if not executable:
        raise DrillError("restic_binary_missing")
    if not Path(executable).is_file():
        raise DrillError("restic_binary_unavailable")

    with TemporaryDirectory(prefix="wp030-restic-synthetic-") as tmp:
        temp = Path(tmp)
        temp.chmod(0o700)
        source = temp / "source"
        repo = temp / "encrypted-repository"
        output = temp / "isolated-restore"
        password_file = temp / "secret-not-exported"
        _generate_fixture(source)

        # Random secret exists only for this test. Do not log, version or
        # expose it as CLI argument/environment value or Actions artifact.
        _private_write(password_file, (secrets.token_urlsafe(48) + "\n").encode())
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(temp),
            "RESTIC_CACHE_DIR": str(temp / "cache"),
            "TMPDIR": str(temp),
        }

        _invoke(executable, repo, password_file, "init", cwd=temp, environment=env)
        _invoke(
            executable, repo, password_file, "backup", str(source),
            "--tag", TAG, "--no-cache",
            cwd=temp, environment=env,
        )
        _invoke(
            executable, repo, password_file, "check", "--read-data", "--no-cache",
            cwd=temp, environment=env,
        )
        # The repository MUST reject an unrelated secret; never print
        # restic's error message, which could contain local fixture paths.
        bad_password_file = temp / "different-temporary-secret"
        _private_write(
            bad_password_file, (secrets.token_urlsafe(48) + "\n").encode()
        )
        try:
            _invoke(
                executable, repo, bad_password_file, "check", "--no-cache",
                cwd=temp, environment=env,
            )
        except DrillError as exc:
            if str(exc) != "restic_check_failed":
                raise
        else:
            raise DrillError("wrong_password_accepted")
        snapshot_response = _invoke(
            executable, repo, password_file, "snapshots", "--json", "--no-cache",
            cwd=temp, environment=env,
        )
        try:
            snapshots = json.loads(snapshot_response)
        except (TypeError, ValueError) as exc:
            raise DrillError("restic_snapshot_result_invalid") from exc
        if (not isinstance(snapshots, list)
                or len(snapshots) != 1
                or not isinstance(snapshots[0], dict)
                or TAG not in snapshots[0].get("tags", [])):
            raise DrillError("restic_snapshot_unexpected")
        # Restore latest into a NEW, private sandbox directory. Restic
        # reconstructs absolute source paths relative to --target.
        output.mkdir(mode=0o700)
        _invoke(
            executable, repo, password_file, "restore", "latest",
            "--target", str(output), "--no-cache",
            cwd=temp, environment=env,
        )
        destination = output / source.relative_to(source.anchor)
        if not _match_bytes(destination):
            raise DrillError("restic_restored_files_mismatch")
        # Only the repository's encrypted objects are scanned. This is
        # an extra leakage smoke check, not formal cryptographic proof.
        for file in repo.rglob("*"):
            if file.is_file():
                value = file.read_bytes()
                if any(blob in value for blob in FILES.values()):
                    raise DrillError("plaintext_found_in_restic_repository")

        report = {
            "kind": "client0_restic_encrypted_recovery_drill",
            "status": "pass",
            "source_classification": "synthetic_only",
            "snapshot_count": 1,
            "restored_files": len(FILES),
            "restic_repo_checked_read_data": True,
            "isolated_restore_verified": True,
            "synthetic_encrypted_repository_verified": True,
            "wrong_password_tested": True,
            "temporary_secret_only": True,
            "real_workspace_accessed": False,
            "real_backup_restore_verified": False,
            "offsite_backup_verified": False,
            "production_backup_authorized": False,
            "external_action_taken": False,
            "customer_data_collected": False,
            "site_published": False,
        }

    # The context manager has removed the disposable repository/secret.
    if temp.exists():
        raise DrillError("temporary_repository_cleanup_failed")
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="WP-030: disposable restic exercise with artificial records only"
    )
    parser.add_argument("--synthetic-drill", action="store_true", required=True)
    parser.parse_args(argv)
    try:
        report = synthetic_drill()
    except DrillError as exc:
        report = {
            "kind": "client0_restic_encrypted_recovery_drill",
            "status": "blocked",
            "reason": str(exc),
            "real_workspace_accessed": False,
            "real_backup_restore_verified": False,
            "production_backup_authorized": False,
            "external_action_taken": False,
        }
        print(json.dumps(report, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

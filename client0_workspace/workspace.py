"""WP-027: private Client 0 workspace preflight and empty-template bootstrap.

Never reads case contents, contacts, ERP, PostgreSQL, Docker or credentials.
The only persisted write is creating missing private directories and a
blank public case template on explicit --bootstrap-empty. No backup claims.
"""

from __future__ import annotations

import argparse
from contextlib import ExitStack
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
from tempfile import TemporaryDirectory
from typing import Any


TEMPLATE = (
    Path(__file__).resolve().parents[1]
    / "docs/operations/templates/client0-case.template.md"
)
PARTS = (".local", "share", "business-automation", "client0")
READ_ONLY_FLAGS = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
FILE_NAME = "case.md"


class WorkspaceError(RuntimeError):
    """Safe failure reason; do not print arbitrary file paths."""


class _Missing(RuntimeError):
    pass


def _check_dir(fd: int, *, private: bool) -> None:
    info = os.fstat(fd)
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        raise WorkspaceError("directory_ownership_or_type_invalid")
    permissions = stat.S_IMODE(info.st_mode)
    if private:
        if permissions != 0o700:
            raise WorkspaceError("private_directory_mode_invalid")
    elif permissions & 0o022:
        raise WorkspaceError("parent_directory_writable_by_others")


def _descend(
    parent_fd: int, name: str, *, create: bool, private: bool
) -> tuple[int, bool]:
    created = False
    try:
        fd = os.open(name, READ_ONLY_FLAGS, dir_fd=parent_fd)
    except FileNotFoundError as exc:
        if not create:
            raise _Missing from exc
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent_fd)
            created = True
        except FileExistsError:
            # Another process may have created it: re-open and validate.
            pass
        except OSError as failure:
            raise WorkspaceError("cannot_create_private_directory") from failure
        try:
            fd = os.open(name, READ_ONLY_FLAGS, dir_fd=parent_fd)
        except OSError as failure:
            raise WorkspaceError("private_directory_changed") from failure
    except OSError as exc:
        raise WorkspaceError("private_directory_unsafe") from exc
    try:
        _check_dir(fd, private=private)
    except Exception:
        os.close(fd)
        raise
    return fd, created


def _check_template_file(
    dir_fd: int,
    *,
    create: bool,
    template_content: bytes | None,
) -> bool:
    """Return True only when our call created a new 0600 blank template."""
    try:
        fd = os.open(FILE_NAME, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=dir_fd)
    except FileNotFoundError as exc:
        if not create:
            raise _Missing from exc
        if not isinstance(template_content, bytes) or not template_content:
            raise WorkspaceError("public_template_unavailable")
        try:
            fd = os.open(
                FILE_NAME,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
                dir_fd=dir_fd,
            )
        except FileExistsError:
            # Respect the existing file; below checks its metadata only.
            return _check_template_file(dir_fd, create=False, template_content=None)
        except OSError as failure:
            raise WorkspaceError("cannot_create_template") from failure
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(template_content)
        except OSError as failure:
            # The file may have been partially written: mark failure.
            # Do not delete it automatically or alter another process's data.
            raise WorkspaceError("template_write_incomplete") from failure
        return True
    except OSError as exc:
        raise WorkspaceError("private_template_unsafe") from exc
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise WorkspaceError("private_template_mode_or_type_invalid")
    finally:
        os.close(fd)
    return False


def _result(status: str, *, created: list[str] | None = None) -> dict[str, Any]:
    return {
        "kind": "client0_private_workspace",
        "status": status,
        "created": created or [],
        "private_root_mode": "0700" if status == "ready" else "unverified",
        "private_template_mode": "0600" if status == "ready" else "unverified",
        "case_contents_inspected": False,
        "customer_data_collected": False,
        "backoffice_operational_verified": False,
        "backup_restore_verified": False,
        "external_action_taken": False,
        "publication_authorized": False,
    }


def workspace_preflight(
    *, home: Path | None = None, bootstrap_empty: bool = False,
    template_path: Path = TEMPLATE,
) -> dict[str, Any]:
    """Preflight without writes, or explicitly create ONLY missing blank structure.

    Real customer case folders or documents are never created or inspected.
    No backups are created; that is a separate WP and human decision.
    """
    root = Path.home() if home is None else home
    template_bytes: bytes | None = None
    if bootstrap_empty:
        try:
            template_bytes = template_path.read_bytes()
        except OSError as exc:
            raise WorkspaceError("public_template_unavailable") from exc
        if (not template_bytes or len(template_bytes) > 64_000 or
                b"MODELO PRIVADO" not in template_bytes or
                "NÃO CONCEDIDA".encode("utf-8") not in template_bytes):
            raise WorkspaceError("public_template_invalid")
    made: list[str] = []
    try:
        home_fd = os.open(root, READ_ONLY_FLAGS)
    except OSError as exc:
        raise WorkspaceError("home_unavailable") from exc
    with ExitStack() as stack:
        stack.callback(os.close, home_fd)
        _check_dir(home_fd, private=False)
        parent = home_fd
        for i, part in enumerate(PARTS):
            private = i >= 2
            try:
                child, created = _descend(
                    parent, part, create=bootstrap_empty, private=private
                )
            except _Missing:
                return _result("missing")
            stack.callback(os.close, child)
            parent = child
            if created:
                made.append(part)
        root_fd = parent
        for part in ("cases", "templates"):
            try:
                child, created = _descend(
                    root_fd, part, create=bootstrap_empty, private=True
                )
            except _Missing:
                return _result("missing")
            stack.callback(os.close, child)
            if created:
                made.append(part)
            if part == "templates":
                try:
                    template_created = _check_template_file(
                        child,
                        create=bootstrap_empty,
                        template_content=template_bytes,
                    )
                except _Missing:
                    return _result("missing")
                if template_created:
                    made.append("templates/case.md")
    return _result("ready", created=made)


def synthetic_drill() -> dict[str, Any]:
    """Exercise empty bootstrap twice, without live HOME or real case files."""
    with TemporaryDirectory(prefix="ba-wp027-synthetic-") as temp:
        home = Path(temp) / "home"
        home.mkdir(mode=0o700)
        first = workspace_preflight(home=home)
        if first["status"] != "missing":
            raise WorkspaceError("synthetic_initial_state_invalid")
        generated = workspace_preflight(home=home, bootstrap_empty=True)
        second = workspace_preflight(home=home, bootstrap_empty=True)
        after = workspace_preflight(home=home)
        copied = home / ".local/share/business-automation/client0/templates/case.md"
        if (generated["status"] != "ready"
                or second["created"]
                or after["status"] != "ready"
                or copied.read_bytes() != TEMPLATE.read_bytes()):
            raise WorkspaceError("synthetic_integrity_failure")
        # No backup created, no claim that a real restore occurred.
        return {
            "kind": "client0_synthetic_workspace_drill",
            "status": "pass",
            "bootstrap_idempotent": True,
            "template_sha256_matches": (
                hashlib.sha256(copied.read_bytes()).hexdigest()
                == hashlib.sha256(TEMPLATE.read_bytes()).hexdigest()
            ),
            "real_workspace_accessed": False,
            "backup_restore_verified": False,
            "external_action_taken": False,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Client0 private empty workspace; never touch case documents."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight", action="store_true", help="read metadata only")
    mode.add_argument("--bootstrap-empty", action="store_true",
                      help="create missing 0700 folders and blank 0600 template")
    mode.add_argument("--synthetic-drill", action="store_true",
                      help="use OS temp files, never real HOME")
    args = parser.parse_args(argv)
    try:
        if args.synthetic_drill:
            outcome = synthetic_drill()
        else:
            outcome = workspace_preflight(bootstrap_empty=args.bootstrap_empty)
    except WorkspaceError as exc:
        print(json.dumps({
            "kind": "client0_private_workspace",
            "status": "blocked",
            "reason": str(exc),
            "backup_restore_verified": False,
            "external_action_taken": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(outcome, sort_keys=True))
    return 0 if outcome["status"] in {"ready", "pass"} else 2


if __name__ == "__main__":
    raise SystemExit(main())

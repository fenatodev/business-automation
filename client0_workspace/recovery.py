"""WP-028: synthetic-only Client 0 index backup/restore rehearsal.

This module intentionally has NO production backup or restore CLI.
ZIP is plaintext and SHA-256 is NOT encryption, authentication or a backup
policy. Never use these internal helpers on live client data.

Only versioned, artificial case.md / proof-social.json references are in
scope. The CLI creates and tests everything in a disposable temp directory.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import sys
from tempfile import TemporaryDirectory
from typing import Any
from zipfile import BadZipFile, ZIP_STORED, ZipFile, ZipInfo

from .workspace import TEMPLATE


CASE_ID = re.compile(r"c0-[0-9]{4}-[0-9]{3}\Z")
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
MAX_FILE = 64 * 1024
MAX_TOTAL = 2 * 1024 * 1024
MAX_FILES = 32
ARCHIVE_NAME = "client0-synthetic-index.zip"
ROOT_SUBDIRS = ("cases", "templates")
MANIFEST_NAME = "manifest.json"


class RecoveryError(ValueError):
    """Never echoes private paths or document contents."""


def _dir(path: Path) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise RecoveryError("private_directory_unavailable") from exc
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or stat.S_IMODE(info.st_mode) != 0o700):
        raise RecoveryError("private_directory_unsafe")


def _read_file(path: Path) -> bytes:
    """Do not follow a file symlink; reject changed or oversized metadata."""
    try:
        before = path.lstat()
        if (not stat.S_ISREG(before.st_mode)
                or before.st_uid != os.geteuid()
                or stat.S_IMODE(before.st_mode) != 0o600
                or not 1 <= before.st_size <= MAX_FILE):
            raise RecoveryError("private_file_unsafe")
        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            after = os.fstat(fd)
            if (not stat.S_ISREG(after.st_mode)
                    or after.st_uid != os.geteuid()
                    or stat.S_IMODE(after.st_mode) != 0o600
                    or after.st_dev != before.st_dev
                    or after.st_ino != before.st_ino
                    or not 1 <= after.st_size <= MAX_FILE):
                raise RecoveryError("private_file_changed")
            data = os.read(fd, MAX_FILE + 1)
            if not 1 <= len(data) <= MAX_FILE:
                raise RecoveryError("private_file_excessive")
            return data
        finally:
            os.close(fd)
    except OSError as exc:
        raise RecoveryError("private_file_unreadable") from exc


def _valid_rel(name: Any) -> bool:
    if name == "templates/case.md":
        return True
    if not isinstance(name, str):
        return False
    parts = name.split("/")
    return (len(parts) == 3 and parts[0] == "cases"
            and CASE_ID.fullmatch(parts[1]) is not None
            and parts[2] in {"case.md", "proof-social.json"})


def _snapshot_entries(root: Path) -> dict[str, bytes]:
    """Bounded whitelist, reject unknown case files or symlinks (test only)."""
    _dir(root)
    for folder in ROOT_SUBDIRS:
        _dir(root / folder)
    names = {entry.name for entry in root.iterdir()}
    if names != set(ROOT_SUBDIRS):
        raise RecoveryError("unknown_root_entry")

    templates = {entry.name for entry in (root / "templates").iterdir()}
    if templates != {"case.md"}:
        raise RecoveryError("unknown_or_missing_template")

    payloads: dict[str, bytes] = {
        "templates/case.md": _read_file(root / "templates/case.md")
    }
    for folder in (root / "cases").iterdir():
        if not CASE_ID.fullmatch(folder.name):
            raise RecoveryError("unknown_case_directory")
        _dir(folder)
        items = {entry.name for entry in folder.iterdir()}
        if "case.md" not in items or not items.issubset(
            {"case.md", "proof-social.json"}
        ):
            raise RecoveryError("unknown_or_missing_case_file")
        for item in sorted(items):
            name = f"cases/{folder.name}/{item}"
            payloads[name] = _read_file(folder / item)
            if len(payloads) > MAX_FILES:
                raise RecoveryError("too_many_files")
    if sum(map(len, payloads.values())) > MAX_TOTAL:
        raise RecoveryError("total_size_exceeded")
    return dict(sorted(payloads.items()))


def _file_manifest(payloads: dict[str, bytes]) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "classification": "synthetic_only_plaintext",
        "files": [
            {
                "path": name,
                "size": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            }
            for name, body in sorted(payloads.items())
        ],
    }


def _json_no_duplicates(pairs: list[tuple[str, Any]]) -> dict:
    output: dict = {}
    for key, value in pairs:
        if key in output:
            raise RecoveryError("duplicate_json_key")
        output[key] = value
    return output


def _validate_manifest(manifest: Any) -> list[dict]:
    if (not isinstance(manifest, dict)
            or set(manifest) != {"schema_version", "classification", "files"}
            or type(manifest["schema_version"]) is not int
            or manifest["schema_version"] != 1
            or manifest["classification"] != "synthetic_only_plaintext"
            or not isinstance(manifest["files"], list)
            or not 1 <= len(manifest["files"]) <= MAX_FILES):
        raise RecoveryError("archive_manifest_invalid")
    entries: list[dict] = []
    names: set[str] = set()
    total = 0
    for entry in manifest["files"]:
        if (not isinstance(entry, dict)
                or set(entry) != {"path", "size", "sha256"}
                or not _valid_rel(entry.get("path"))
                or type(entry.get("size")) is not int
                or not 1 <= entry["size"] <= MAX_FILE
                or not isinstance(entry.get("sha256"), str)
                or not SHA256.fullmatch(entry["sha256"])):
            raise RecoveryError("archive_manifest_file_invalid")
        name = entry["path"]
        if name in names:
            raise RecoveryError("archive_duplicate_path")
        names.add(name)
        total += entry["size"]
        entries.append(entry)
    if total > MAX_TOTAL or "templates/case.md" not in names:
        raise RecoveryError("archive_manifest_incomplete")
    cases: dict[str, set[str]] = {}
    for name in names:
        if name.startswith("cases/"):
            parts = name.split("/")
            cases.setdefault(parts[1], set()).add(parts[2])
    if any("case.md" not in files for files in cases.values()):
        raise RecoveryError("archive_missing_case_index")
    return entries


def _archive_member(name: str, data: bytes) -> tuple[ZipInfo, bytes]:
    info = ZipInfo(name)
    info.compress_type = ZIP_STORED
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | 0o600) << 16
    return info, data


def _write_synthetic_snapshot(root: Path, archive: Path) -> dict:
    """Test helper only; creates a PLAINTEXT archive with O_EXCL / 0600."""
    payloads = _snapshot_entries(root)
    if archive.is_symlink() or archive.exists():
        raise RecoveryError("archive_destination_exists")
    _dir(archive.parent)
    manifest = json.dumps(
        _file_manifest(payloads), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    try:
        fd = os.open(
            archive, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(fd, "wb") as output:
            with ZipFile(output, "w", compression=ZIP_STORED) as bundle:
                info, value = _archive_member(MANIFEST_NAME, manifest)
                bundle.writestr(info, value)
                for name, value in payloads.items():
                    info, data = _archive_member(name, value)
                    bundle.writestr(info, data)
    except OSError as exc:
        raise RecoveryError("archive_write_failed") from exc
    return {
        "snapshot_files": len(payloads),
        "snapshot_sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
        "encrypted": False,
    }


def _read_validated_snapshot(archive: Path) -> dict[str, bytes]:
    """Treat ZIP members as untrusted; extract only validated listed entries."""
    try:
        blob = _read_file(archive) if archive.stat().st_size <= MAX_FILE else None
        # Archives can be larger than one individual source file.
        if blob is None:
            info = archive.lstat()
            if (not stat.S_ISREG(info.st_mode)
                    or info.st_uid != os.geteuid()
                    or stat.S_IMODE(info.st_mode) != 0o600
                    or not 1 <= info.st_size <= MAX_TOTAL + 16_384):
                raise RecoveryError("archive_file_unsafe")
            fd = os.open(archive, os.O_RDONLY | os.O_NOFOLLOW)
            try:
                blob = os.read(fd, MAX_TOTAL + 16_385)
            finally:
                os.close(fd)
            if len(blob) > MAX_TOTAL + 16_384:
                raise RecoveryError("archive_too_large")
        from io import BytesIO
        with ZipFile(BytesIO(blob), "r") as zf:
            infos = zf.infolist()
            names = [info.filename for info in infos]
            if (len(names) != len(set(names)) or not 2 <= len(names) <= MAX_FILES + 1
                    or names[0] != MANIFEST_NAME):
                raise RecoveryError("archive_members_invalid")
            for item in infos:
                mode = (item.external_attr >> 16) & 0o170000
                if (item.compress_type != ZIP_STORED or item.is_dir()
                        or mode != stat.S_IFREG
                        or item.flag_bits & 0x1
                        or item.file_size > MAX_FILE
                        or item.compress_size != item.file_size):
                    raise RecoveryError("archive_member_unsafe")
            manifest_raw = zf.read(MANIFEST_NAME)
            if len(manifest_raw) > MAX_FILE:
                raise RecoveryError("archive_manifest_excessive")
            manifest = json.loads(
                manifest_raw.decode("utf-8"), object_pairs_hook=_json_no_duplicates
            )
            entries = _validate_manifest(manifest)
            if set(names[1:]) != {entry["path"] for entry in entries}:
                raise RecoveryError("archive_content_mismatch")
            payloads: dict[str, bytes] = {}
            for item in entries:
                name = item["path"]
                value = zf.read(name)
                if (len(value) != item["size"]
                        or hashlib.sha256(value).hexdigest() != item["sha256"]):
                    raise RecoveryError("archive_checksum_failed")
                payloads[name] = value
            return payloads
    except (OSError, UnicodeError, BadZipFile, KeyError, ValueError, EOFError) as exc:
        if isinstance(exc, RecoveryError):
            raise
        raise RecoveryError("archive_invalid_or_unreadable") from exc


def _restore_synthetic_snapshot(archive: Path, destination: Path) -> dict:
    """Fail BEFORE creating the target on malformed archive or existing path."""
    payloads = _read_validated_snapshot(archive)
    if destination.exists() or destination.is_symlink():
        raise RecoveryError("restore_destination_exists")
    _dir(destination.parent)
    try:
        destination.mkdir(mode=0o700)
        for name in ROOT_SUBDIRS:
            (destination / name).mkdir(mode=0o700)
        folders = sorted({
            destination / name.split("/")[0] / name.split("/")[1]
            for name in payloads if name.startswith("cases/")
        })
        for folder in folders:
            folder.mkdir(mode=0o700)
        for name, data in sorted(payloads.items()):
            target = destination.joinpath(*name.split("/"))
            fd = os.open(
                target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600,
            )
            with os.fdopen(fd, "wb") as output:
                output.write(data)
    except OSError as exc:
        raise RecoveryError("restore_write_failed") from exc

    restored = _snapshot_entries(destination)
    if restored != payloads:
        raise RecoveryError("restore_integrity_failed")
    return {"status": "pass", "restored_files": len(restored)}


def synthetic_drill() -> dict[str, Any]:
    """Exercise only a disposable artificial Client 0 index and restore."""
    with TemporaryDirectory(prefix="ba-wp028-recovery-") as directory:
        temp = Path(directory)
        temp.chmod(0o700)
        source = temp / "source"
        source.mkdir(mode=0o700)
        for part in ROOT_SUBDIRS:
            (source / part).mkdir(mode=0o700)
        case = source / "cases" / "c0-2026-001"
        case.mkdir(mode=0o700)
        for path, data in (
            (source / "templates/case.md", TEMPLATE.read_bytes()),
            (case / "case.md",
             b"# SIMULADO - sem cliente real\nSYN-OPP-001\nSYN-QUOTE-V1\n"),
            (case / "proof-social.json",
             b'{"schema_version":1,"classification":"unverified","consents":[]}\n'),
        ):
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as output:
                output.write(data)
        snapshot = temp / ARCHIVE_NAME
        manifest = _write_synthetic_snapshot(source, snapshot)
        before = _snapshot_entries(source)
        restored_to = temp / "restored"
        result = _restore_synthetic_snapshot(snapshot, restored_to)
        if _snapshot_entries(restored_to) != before:
            raise RecoveryError("synthetic_restore_mismatch")
        return {
            "kind": "client0_synthetic_index_recovery",
            "status": result["status"],
            "source_classification": "synthetic_only",
            "snapshot_files": manifest["snapshot_files"],
            "restored_files": result["restored_files"],
            "integrity_sha256_verified": True,
            "restore_isolated": True,
            "archive_encrypted": False,
            "real_workspace_accessed": False,
            "real_backup_restore_verified": False,
            "production_backup_authorized": False,
            "external_action_taken": False,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="WP-028: synthetic ONLY; plaintext files never leave OS temp."
    )
    parser.add_argument("--synthetic-drill", action="store_true", required=True)
    parser.parse_args(argv)
    try:
        report = synthetic_drill()
    except RecoveryError as exc:
        print(json.dumps({
            "kind": "client0_synthetic_index_recovery",
            "status": "blocked",
            "reason": str(exc),
            "real_backup_restore_verified": False,
            "production_backup_authorized": False,
            "external_action_taken": False,
        }, sort_keys=True))
        return 2
    print(json.dumps(report, sort_keys=True))
    return 0 if report["status"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(main())

"""WP-023 / O08 — read-only evidence readiness, never publication authorization.

Accepts private case metadata only. Presence of a reference or a checkbox
does not prove consent, identity, accuracy, lawful retention or publication
rights. Human review remains mandatory in every outcome.
"""

from __future__ import annotations

import argparse
from datetime import date
import json
import math
import os
from pathlib import Path
import re
import stat
from typing import Any


USES = frozenset({"metrics", "identity", "logo", "testimonial", "image"})
CHANNELS = frozenset({"linkedin", "site"})
CASE_ID = re.compile(r"c0-[0-9]{4}-[0-9]{3}")
DIGEST = re.compile(r"[0-9a-f]{64}")
REF = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{4,95}")
MAX_BYTES = 64 * 1024
TEMPLATE = Path(__file__).resolve().parents[1] / "docs/operations/templates/client0-proof-social.template.json"


class EvidenceError(ValueError):
    """Metadata cannot be read safely. Contents are never echoed."""


def _reference(value: Any) -> bool:
    return isinstance(value, str) and REF.fullmatch(value) is not None


def _day(value: Any) -> date | None:
    if not isinstance(value, str) or len(value) != 10:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
    )


def _add(blockers: list[str], issue: str) -> None:
    if issue not in blockers:
        blockers.append(issue)


def _check_measurement(record: dict, blockers: list[str], today: date) -> None:
    metric = record.get("metric")
    if not isinstance(metric, dict):
        _add(blockers, "measurement_missing")
        return
    if not (_reference(metric.get("metric_id")) and
            _reference(metric.get("method_ref")) and
            _reference(metric.get("comparability_review_ref"))):
        _add(blockers, "measurement_method_unverified")
    unit = metric.get("unit")
    if not isinstance(unit, str) or unit not in {"minutes", "hours", "count", "percent"}:
        _add(blockers, "measurement_unit_invalid")
    intervals: list[tuple[date, date]] = []
    provenance: list[str] = []
    for phase in ("before", "after"):
        part = metric.get(phase)
        if not isinstance(part, dict):
            _add(blockers, "measurement_pair_incomplete")
            continue
        if not _number(part.get("value")) or part.get("kind") != "observed":
            _add(blockers, "measurement_not_observed")
        if not _reference(part.get("source_ref")):
            _add(blockers, "measurement_source_missing")
        else:
            provenance.append(part["source_ref"])
        start, end = _day(part.get("period_start")), _day(part.get("period_end"))
        if start is None or end is None or start > end or end > today:
            _add(blockers, "measurement_period_invalid")
        else:
            intervals.append((start, end))
    if len(intervals) == 2 and intervals[0][1] >= intervals[1][0]:
        _add(blockers, "measurement_periods_overlap")
    if len(provenance) == 2 and provenance[0] == provenance[1]:
        _add(blockers, "measurement_same_evidence_reference")


def _check_grants(record: dict, blockers: list[str], today: date) -> None:
    asset = record.get("asset")
    if not isinstance(asset, dict):
        _add(blockers, "public_asset_missing")
        return
    digest = asset.get("sha256")
    channel = asset.get("channel")
    uses = asset.get("requested_uses")
    if not isinstance(digest, str) or not DIGEST.fullmatch(digest):
        _add(blockers, "public_asset_digest_invalid")
    if channel not in CHANNELS:
        _add(blockers, "publication_channel_unsupported")
    if not _reference(asset.get("sanitized_ref")) or not _reference(asset.get("version_ref")):
        _add(blockers, "public_asset_review_missing")
    if (
        not isinstance(uses, list)
        or not uses
        or len(uses) != len(set(str(u) for u in uses))
        or not all(isinstance(u, str) and u in USES for u in uses)
        or "metrics" not in uses
    ):
        _add(blockers, "requested_uses_invalid")
        return

    grants = record.get("consents")
    if not isinstance(grants, list):
        _add(blockers, "explicit_consent_missing")
        return
    for requested in uses:
        valid = False
        revoked_match = False
        for grant in grants:
            if not isinstance(grant, dict):
                continue
            if (grant.get("use") != requested or grant.get("channel") != channel
                    or grant.get("asset_sha256") != digest):
                continue
            if grant.get("revoked_at") is not None:
                revoked_match = True
                continue
            given, expiry = _day(grant.get("granted_at")), _day(grant.get("expires_at"))
            if (
                _reference(grant.get("authorization_ref"))
                and _reference(grant.get("authority_review_ref"))
                and given is not None
                and given <= today
                and (expiry is None if grant.get("expires_at") is None else expiry is not None)
                and (expiry is None or expiry >= today)
            ):
                valid = True
        if revoked_match:
            _add(blockers, "consent_revoked")
        if not valid:
            _add(blockers, f"consent_missing_or_expired:{requested}")


def assess(record: Any, *, today: date | None = None) -> dict[str, Any]:
    """Return sanitized blockers. Even a complete record is NOT publishable."""
    day = today or date.today()
    blockers: list[str] = []
    if not isinstance(record, dict):
        blockers.append("invalid_record")
    else:
        if record.get("schema_version") != 1:
            _add(blockers, "schema_unsupported")
        if not isinstance(record.get("case_ref"), str) or CASE_ID.fullmatch(
            record["case_ref"]
        ) is None:
            _add(blockers, "case_reference_invalid")
        if record.get("classification") != "real_verified":
            _add(blockers, "real_case_not_verified")
        evidence = record.get("evidence")
        required = (
            "commercial_acceptance_ref", "technical_acceptance_ref",
            "rights_review_ref", "privacy_review_ref", "editorial_review_ref",
        )
        if not isinstance(evidence, dict) or not all(
            _reference(evidence.get(field)) for field in required
        ):
            _add(blockers, "independent_evidence_incomplete")
        _check_measurement(record, blockers, day)
        _check_grants(record, blockers, day)
        if record.get("withdrawal_requested") is not False:
            _add(blockers, "withdrawal_or_status_unknown")
    return {
        "status": "blocked" if blockers else "human_review_required",
        "blocking_codes": sorted(blockers),
        "publication_authorized": False,
        "external_action_taken": False,
        "human_review_required": True,
    }


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict:
    result: dict = {}
    for key, value in pairs:
        if key in result:
            raise EvidenceError("duplicate_json_key")
        result[key] = value
    return result


def _private_directory(path: Path) -> None:
    try:
        mode = path.lstat()
    except OSError as exc:
        raise EvidenceError("private_directory_missing") from exc
    if not (
        stat.S_ISDIR(mode.st_mode)
        and mode.st_uid == os.geteuid()
        and (mode.st_mode & 0o777) == 0o700
    ):
        raise EvidenceError("private_directory_unsafe")


def read_private_case(path: Path, *, cases_root: Path | None = None) -> Any:
    """Strictly read one 0600 file in a 0700 Client0 cases subdirectory."""
    root = cases_root or Path.home() / ".local/share/business-automation/client0/cases"
    _private_directory(root)
    if (
        path.name != "proof-social.json"
        or path.parent.parent != root
        or CASE_ID.fullmatch(path.parent.name) is None
    ):
        raise EvidenceError("outside_private_case_layout")
    _private_directory(path.parent)
    try:
        info = path.lstat()
        if not (
            stat.S_ISREG(info.st_mode)
            and info.st_uid == os.geteuid()
            and (info.st_mode & 0o777) == 0o600
            and info.st_size <= MAX_BYTES
        ):
            raise EvidenceError("private_file_unsafe")
        descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        try:
            checked = os.fstat(descriptor)
            if not (
                stat.S_ISREG(checked.st_mode)
                and checked.st_ino == info.st_ino
                and checked.st_dev == info.st_dev
                and checked.st_uid == os.geteuid()
                and (checked.st_mode & 0o777) == 0o600
                and checked.st_size <= MAX_BYTES
            ):
                raise EvidenceError("private_file_changed")
            raw = os.read(descriptor, MAX_BYTES + 1)
        finally:
            os.close(descriptor)
        if len(raw) > MAX_BYTES:
            raise EvidenceError("private_file_excessive")
        record = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_no_duplicate_keys,
            parse_constant=lambda unused: (_ for _ in ()).throw(EvidenceError("invalid_number")),
        )
        if not isinstance(record, dict) or record.get("case_ref") != path.parent.name:
            raise EvidenceError("case_reference_mismatch")
        return record
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvidenceError("private_file_unreadable") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="WP-023: verificar evidências; JAMAIS autorizar publicação."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--template-check", action="store_true", help="somente modelo público")
    mode.add_argument("--check-private", type=Path, metavar="PATH", help="somente case privado")
    args = parser.parse_args(argv)
    try:
        if args.template_check:
            raw = TEMPLATE.read_text(encoding="utf-8")
            record = json.loads(raw, object_pairs_hook=_no_duplicate_keys)
        else:
            record = read_private_case(args.check_private)
        report = assess(record)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 0 if not args.check_private else (0 if not report["blocking_codes"] else 2)
    except (OSError, UnicodeError, json.JSONDecodeError, EvidenceError) as exc:
        # Never print an arbitrary data path, record body, evidence or identity.
        print(json.dumps({
            "status": "blocked",
            "blocking_codes": ["metadata_unreadable"],
            "publication_authorized": False,
            "external_action_taken": False,
            "human_review_required": True,
        }, sort_keys=True))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

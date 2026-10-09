"""WP-023: only synthetic evidence, temporary private directories and no network."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import subprocess
import sys

import pytest

from proof_social.checklist import (
    EvidenceError,
    TEMPLATE,
    assess,
    read_private_case,
)

TODAY = date(2026, 10, 8)
DIGEST = "a" * 64


def complete_synthetic_structure() -> dict:
    """A wholly INVENTED contract-like test fixture, never a real customer."""
    return {
        "schema_version": 1,
        "case_ref": "c0-2026-001",
        # In tests ONLY, simulate all required metadata being manually supplied.
        "classification": "real_verified",
        "withdrawal_requested": False,
        "evidence": {
            "commercial_acceptance_ref": "ev-contract-001",
            "technical_acceptance_ref": "ev-accept-002",
            "rights_review_ref": "ev-rights-003",
            "privacy_review_ref": "ev-privacy-004",
            "editorial_review_ref": "ev-edit-005",
        },
        "metric": {
            "metric_id": "metric-task-time",
            "unit": "minutes",
            "method_ref": "ev-method-001",
            "comparability_review_ref": "ev-review-002",
            "before": {
                "kind": "observed",
                "value": 12.0,
                "source_ref": "ev-before-001",
                "period_start": "2026-09-01",
                "period_end": "2026-09-07",
            },
            "after": {
                "kind": "observed",
                "value": 9.0,
                "source_ref": "ev-after-002",
                "period_start": "2026-09-14",
                "period_end": "2026-09-20",
            },
        },
        "asset": {
            "version_ref": "asset-v001",
            "sanitized_ref": "ev-redacted-003",
            "sha256": DIGEST,
            "channel": "linkedin",
            "requested_uses": ["metrics"],
        },
        "consents": [
            {
                "use": "metrics",
                "channel": "linkedin",
                "asset_sha256": DIGEST,
                "authorization_ref": "ev-grant-001",
                "authority_review_ref": "ev-owner-002",
                "granted_at": "2026-09-24",
                "expires_at": "2026-12-31",
                "revoked_at": None,
            }
        ],
    }


def check(record: dict) -> dict:
    return assess(record, today=TODAY)


def test_template_is_explicitly_unverified_and_has_no_grants() -> None:
    template = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    assert template["classification"] == "unverified"
    assert template["consents"] == []
    report = check(template)
    assert report["status"] == "blocked"
    assert "real_case_not_verified" in report["blocking_codes"]
    assert report["publication_authorized"] is False


def test_even_complete_mock_record_cannot_grant_publication() -> None:
    result = check(complete_synthetic_structure())
    assert result == {
        "status": "human_review_required",
        "blocking_codes": [],
        "publication_authorized": False,
        "external_action_taken": False,
        "human_review_required": True,
    }


@pytest.mark.parametrize("change,code", [
    ({"classification": "synthetic"}, "real_case_not_verified"),
    ({"withdrawal_requested": None}, "withdrawal_or_status_unknown"),
    ({"withdrawal_requested": True}, "withdrawal_or_status_unknown"),
    ({"schema_version": 2}, "schema_unsupported"),
    ({"case_ref": "Acme Industrial Ltda"}, "case_reference_invalid"),
    ({"evidence": None}, "independent_evidence_incomplete"),
    ({"consents": []}, "consent_missing_or_expired:metrics"),
    ({"asset": {}}, "public_asset_digest_invalid"),
])
def test_missing_prerequisites_are_blocked(change: dict, code: str) -> None:
    case = complete_synthetic_structure()
    case.update(change)
    assert code in check(case)["blocking_codes"]


def test_measurements_must_be_two_distinct_observations() -> None:
    case = complete_synthetic_structure()
    case["metric"]["before"]["value"] = True
    case["metric"]["after"]["kind"] = "estimated"
    case["metric"]["before"]["source_ref"] = case["metric"]["after"]["source_ref"]
    codes = check(case)["blocking_codes"]
    assert "measurement_not_observed" in codes
    assert "measurement_same_evidence_reference" in codes


@pytest.mark.parametrize("start,end,expected", [
    ("2026-10-10", "2026-10-11", "measurement_period_invalid"),
    ("2026-09-30", "2026-09-01", "measurement_period_invalid"),
    ("2026-09-03", "2026-09-10", "measurement_periods_overlap"),
    ("not-a-date", "2026-10-01", "measurement_period_invalid"),
])
def test_period_comparability_rules_block_bad_sequences(
    start: str, end: str, expected: str
) -> None:
    case = complete_synthetic_structure()
    case["metric"]["after"]["period_start"] = start
    case["metric"]["after"]["period_end"] = end
    assert expected in check(case)["blocking_codes"]


def test_missing_measurement_method_and_comparability_review_block() -> None:
    case = complete_synthetic_structure()
    case["metric"]["comparability_review_ref"] = ""
    case["metric"]["method_ref"] = ""
    assert "measurement_method_unverified" in check(case)["blocking_codes"]


def test_consent_is_individual_per_use_and_channel() -> None:
    case = complete_synthetic_structure()
    case["asset"]["requested_uses"] = ["metrics", "identity", "logo"]
    assert "consent_missing_or_expired:identity" in check(case)["blocking_codes"]
    assert "consent_missing_or_expired:logo" in check(case)["blocking_codes"]
    for use in ("identity", "logo"):
        grant = deepcopy(case["consents"][0])
        grant["use"] = use
        grant["authorization_ref"] = "ev-grant-"+use
        case["consents"].append(grant)
    assert check(case)["status"] == "human_review_required"
    assert check(case)["publication_authorized"] is False


def test_revocation_always_blocks_even_with_another_matching_grant() -> None:
    case = complete_synthetic_structure()
    former = deepcopy(case["consents"][0])
    former["revoked_at"] = "2026-10-01"
    case["consents"].append(former)
    assert "consent_revoked" in check(case)["blocking_codes"]


@pytest.mark.parametrize("field,value", [
    ("asset_sha256", "b" * 64),
    ("channel", "site"),
    ("expires_at", "2026-10-01"),
    ("granted_at", "2026-10-09"),
    ("authority_review_ref", ""),
    ("authorization_ref", ""),
])
def test_wrong_scope_expiry_or_missing_proof_blocks_consent(field: str, value: str) -> None:
    case = complete_synthetic_structure()
    case["consents"][0][field] = value
    assert "consent_missing_or_expired:metrics" in check(case)["blocking_codes"]


def test_malformed_channel_and_huge_number_fail_closed_without_exception() -> None:
    case = complete_synthetic_structure()
    case["asset"]["channel"] = ["linkedin"]
    case["metric"]["before"]["value"] = 10 ** 600
    codes = check(case)["blocking_codes"]
    assert "publication_channel_unsupported" in codes
    assert "measurement_not_observed" in codes


def test_public_asset_requires_immutable_version_and_review() -> None:
    case = complete_synthetic_structure()
    case["asset"]["sha256"] = "short"
    case["asset"]["sanitized_ref"] = ""
    case["asset"]["version_ref"] = ""
    codes = check(case)["blocking_codes"]
    assert "public_asset_digest_invalid" in codes
    assert "public_asset_review_missing" in codes


def test_invalid_or_duplicate_uses_block() -> None:
    case = complete_synthetic_structure()
    case["asset"]["requested_uses"] = ["metrics", "metrics"]
    assert "requested_uses_invalid" in check(case)["blocking_codes"]
    case["asset"]["requested_uses"] = ["testimonials", "metrics"]
    assert "requested_uses_invalid" in check(case)["blocking_codes"]


def _private_fixture(tmp_path: Path, case: dict | None = None) -> tuple[Path, Path]:
    root = tmp_path / "cases"
    root.mkdir(mode=0o700)
    folder = root / "c0-2026-001"
    folder.mkdir(mode=0o700)
    path = folder / "proof-social.json"
    path.write_text(
        json.dumps(complete_synthetic_structure() if case is None else case),
        encoding="utf-8",
    )
    path.chmod(0o600)
    return root, path


def test_private_read_only_file_is_loaded_without_touching_business_data(tmp_path: Path) -> None:
    root, path = _private_fixture(tmp_path)
    original = path.read_bytes()
    record = read_private_case(path, cases_root=root)
    assert record["case_ref"] == "c0-2026-001"
    assert check(record)["publication_authorized"] is False
    assert path.read_bytes() == original


def test_unsafe_permissions_are_rejected(tmp_path: Path) -> None:
    root, path = _private_fixture(tmp_path)
    path.chmod(0o644)
    with pytest.raises(EvidenceError, match="private_file_unsafe"):
        read_private_case(path, cases_root=root)
    path.chmod(0o600)
    root.chmod(0o755)
    with pytest.raises(EvidenceError, match="private_directory_unsafe"):
        read_private_case(path, cases_root=root)


def test_symlink_is_rejected(tmp_path: Path) -> None:
    root, path = _private_fixture(tmp_path)
    link = path.parent / "alias.json"
    link.symlink_to(path)
    with pytest.raises(EvidenceError, match="outside_private_case_layout"):
        read_private_case(link, cases_root=root)
    path.unlink()
    path.symlink_to(link)
    with pytest.raises(EvidenceError, match="private_file_unsafe"):
        read_private_case(path, cases_root=root)


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    root, path = _private_fixture(tmp_path)
    path.write_text('{"case_ref":"c0-2026-001","case_ref":"c0-2026-001"}')
    with pytest.raises(EvidenceError, match="duplicate_json_key"):
        read_private_case(path, cases_root=root)


def test_case_reference_mismatch_is_rejected(tmp_path: Path) -> None:
    root, path = _private_fixture(tmp_path)
    record = complete_synthetic_structure()
    record["case_ref"] = "c0-2026-002"
    path.write_text(json.dumps(record))
    with pytest.raises(EvidenceError, match="case_reference_mismatch"):
        read_private_case(path, cases_root=root)


def test_arbitrary_large_private_file_is_rejected(tmp_path: Path) -> None:
    root, path = _private_fixture(tmp_path)
    path.write_bytes(b"x" * (65536 + 1))
    with pytest.raises(EvidenceError, match="private_file_unsafe"):
        read_private_case(path, cases_root=root)


def test_template_cli_returns_blocked_sanitized_without_network() -> None:
    run = subprocess.run(
        [sys.executable, "-m", "proof_social.checklist", "--template-check"],
        capture_output=True, text=True, check=True,
    )
    report = json.loads(run.stdout)
    assert report["status"] == "blocked"
    assert report["publication_authorized"] is False
    assert report["external_action_taken"] is False
    assert "c0-0000" not in run.stdout
    assert "https:" not in run.stdout
    assert run.stderr == ""

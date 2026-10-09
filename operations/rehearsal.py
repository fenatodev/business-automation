"""WP-024: pure, offline rehearsal of F2 process gates with invented metadata.

This module cannot send a proposal, charge, certify a client, or authorize
publication. Every reported "success" concerns only a synthetic sequence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
from typing import Any


FIXTURE = Path(__file__).with_name("fixtures") / "wp024-synthetic-cycle.json"

GATES = (
    "G0", "G1", "G2", "G3", "G4a", "G4b",
    "G5", "G6", "G7", "G8", "G9", "G10",
)
ROLES = {
    "G0": "operator",
    "G1": "technical",
    "G2": "backoffice",
    "G3": "backoffice",
    "G4a": "commercial",
    "G4b": "commercial",
    "G5": "commercial",
    "G6": "technical",
    "G7": "technical",
    "G8": "finance",
    "G9": "finance",
    "G10": "support",
}
NEEDS = {
    "G0": (),
    "G1": ("G0",),
    "G2": ("G1",),
    "G3": ("G2",),
    "G4a": ("G3",),
    "G4b": ("G4a",),
    "G5": ("G4b",),
    "G6": ("G5",),
    "G7": ("G6",),
    "G8": ("G5",),
    "G9": ("G8",),
    "G10": ("G7",),
}
REF = re.compile(r"SYN-[A-Z0-9]+(?:-[A-Z0-9]+)*", flags=re.ASCII)
BILLING = {"upfront": "G5", "milestone": "G6", "after_delivery": "G7"}
LIVE_GAPS = (
    "commercial_pricing_and_terms_unverified",
    "real_backoffice_erp_or_manual_authority_unverified",
    "real_contract_send_and_customer_acceptance_missing",
    "real_delivery_and_acceptance_missing",
    "real_receivable_and_bank_reconciliation_missing",
    "private_case_backup_restore_not_proven",
    "site_brand_contact_and_publication_pending_review",
    "real_metrics_and_case_disclosure_consent_missing",
)


def _report(
    completed: set[str],
    *,
    code: str | None,
    gate: str | None,
    finance: str,
) -> dict[str, Any]:
    """Even a successful rehearsal has no authority or live success."""
    return {
        "kind": "synthetic_f2_operational_rehearsal",
        "simulation_result": "blocked" if code else "simulated_sequence_complete",
        "completed_simulated_gates": [item for item in GATES if item in completed],
        "finance_projection": finance,
        "blocking_codes": [] if code is None else [code],
        "blocked_at": gate if code else None,
        "known_live_gaps": list(LIVE_GAPS),
        "commercial_success": False,
        "f2_exit_met": False,
        "contact_authorized": False,
        "proposals_sent": False,
        "publication_authorized": False,
        "external_action_taken": False,
    }


def _synthetic_ref(value: Any) -> bool:
    return isinstance(value, str) and REF.fullmatch(value) is not None


def assess_scenario(scenario: Any) -> dict[str, Any]:
    """Validate one synthetic gate sequence; no IO and no state changes."""
    completed: set[str] = set()
    finance = "not_simulated"

    def stop(reason: str, gate: str | None = None) -> dict[str, Any]:
        return _report(completed, code=reason, gate=gate, finance=finance)

    if not isinstance(scenario, dict) or set(scenario) != {
        "schema_version", "kind", "scenario_ref", "tenant_ref",
        "opportunity_ref", "billing_trigger", "events",
    }:
        return stop("scenario_schema_invalid")

    if (
        type(scenario["schema_version"]) is not int
        or scenario["schema_version"] != 1
        or scenario["kind"] != "synthetic_offline"
        or not all(_synthetic_ref(scenario[k]) for k in (
            "scenario_ref", "tenant_ref", "opportunity_ref"
        ))
    ):
        return stop("scenario_not_synthetic")

    billing = scenario["billing_trigger"]
    if not isinstance(billing, str) or billing not in BILLING:
        return stop("billing_trigger_invalid")

    events = scenario["events"]
    if not isinstance(events, list) or not 1 <= len(events) <= 32:
        return stop("event_list_invalid")

    versions: dict[str, str] = {}
    evidence_seen: set[str] = set()
    partial_seen = False

    for event in events:
        if not isinstance(event, dict) or set(event) != {
            "gate", "actor", "evidence_ref", "version", "outcome",
        }:
            return stop("event_schema_invalid")
        gate = event["gate"]
        if not isinstance(gate, str) or gate not in ROLES:
            return stop("unknown_gate")
        if event["actor"] != ROLES[gate]:
            return stop("wrong_actor", gate)
        if not _synthetic_ref(event["evidence_ref"]) or not _synthetic_ref(
            event["version"]
        ):
            return stop("unverifiable_synthetic_reference", gate)
        if event["evidence_ref"] in evidence_seen:
            return stop("repeated_evidence_reference", gate)
        evidence_seen.add(event["evidence_ref"])

        if gate in completed and gate != "G9":
            return stop("duplicate_gate", gate)
        if any(required not in completed for required in NEEDS[gate]):
            return stop("prerequisite_missing", gate)

        outcome = event["outcome"]
        if not isinstance(outcome, str):
            return stop("invalid_outcome", gate)
        if outcome == "unknown" and gate in {"G2", "G3", "G9"}:
            return stop("unresolved_remote_outcome", gate)
        if gate == "G9":
            if outcome not in {"partial", "settled", "reversed", "overdue"}:
                return stop("invalid_finance_outcome", gate)
            if gate in completed:
                if not partial_seen or outcome != "settled":
                    return stop("invalid_finance_reconciliation", gate)
                # Exactly one separately evidenced partial -> settled correction.
                partial_seen = False
            elif outcome == "settled":
                # A directly settled, independently evidenced invoice is valid.
                pass
            elif outcome == "partial":
                partial_seen = True
            else:
                return stop("finance_not_settled", gate)
            finance = "simulated_" + outcome
        elif outcome != "simulated":
            return stop("not_a_simulated_gate", gate)

        # G8 is controlled by a contract trigger, not by always reaching G7.
        if gate == "G8" and BILLING[billing] not in completed:
            return stop("billing_trigger_not_met", gate)

        # Evidence for a formal proposal, delivery and receivable must refer
        # to EXACTLY the version that was introduced for that artifact.
        for introduction, family in (
            ("G3", ("G3", "G4a", "G4b", "G5")),
            ("G6", ("G6", "G7")),
            ("G8", ("G8", "G9")),
        ):
            if gate not in family:
                continue
            if gate == introduction:
                versions[introduction] = event["version"]
            elif event["version"] != versions.get(introduction):
                return stop("version_mismatch", gate)

        completed.add(gate)

    missing = [gate for gate in GATES if gate not in completed]
    if missing:
        return stop("required_simulated_gate_missing", missing[0])
    if finance != "simulated_settled":
        return stop("finance_not_settled", "G9")
    return _report(completed, code=None, gate=None, finance=finance)


def run_fixture() -> dict[str, Any]:
    """The only CLI input is a repository-pinned fictitious JSON fixture."""
    with FIXTURE.open(encoding="utf-8") as handle:
        return assess_scenario(json.load(handle))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WP-024: offline F2 simulation only")
    parser.add_argument("--run", action="store_true", required=True)
    parser.parse_args(argv)
    try:
        result = run_fixture()
    except (OSError, UnicodeError, ValueError):
        result = _report(set(), code="fixture_unreadable", gate=None,
                         finance="not_simulated")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if result["simulation_result"] == "simulated_sequence_complete" else 2


if __name__ == "__main__":
    raise SystemExit(main())

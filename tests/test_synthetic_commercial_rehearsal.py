"""WP-024: contract tests using only invented IDs; no APIs, DB or IO writes."""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys

import pytest

from operations.rehearsal import BILLING, FIXTURE, GATES, LIVE_GAPS, assess_scenario, run_fixture


def scenario() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def edit_gate(case: dict, gate: str, occurrence: int = 0) -> dict:
    matches = [event for event in case["events"] if event["gate"] == gate]
    return matches[occurrence]


def assert_not_real(result: dict) -> None:
    for field in (
        "commercial_success", "f2_exit_met", "contact_authorized",
        "proposals_sent", "publication_authorized", "external_action_taken",
    ):
        assert result[field] is False, field
    assert result["known_live_gaps"] == list(LIVE_GAPS)


def test_full_synthetic_cycle_includes_every_gate_and_separate_finance_updates() -> None:
    result = run_fixture()
    assert result["kind"] == "synthetic_f2_operational_rehearsal"
    assert result["simulation_result"] == "simulated_sequence_complete"
    assert result["completed_simulated_gates"] == list(GATES)
    assert len(result["completed_simulated_gates"]) == 12
    assert result["blocking_codes"] == []
    assert result["blocked_at"] is None
    assert result["finance_projection"] == "simulated_settled"
    assert_not_real(result)

    events = scenario()["events"]
    assert [event["outcome"] for event in events if event["gate"] == "G9"] == [
        "partial", "settled"
    ]
    assert events[4]["gate"] == "G4a"
    assert events[5]["gate"] == "G4b"


def test_rehearsal_is_deterministic_and_does_not_mutate_the_scenario() -> None:
    case = scenario()
    initial = deepcopy(case)
    assert assess_scenario(case) == assess_scenario(case)
    assert case == initial


def test_cli_outputs_only_safe_json_with_no_unauthorized_success() -> None:
    p = subprocess.run(
        [sys.executable, "-m", "operations.rehearsal", "--run"],
        capture_output=True, check=True, text=True,
    )
    assert json.loads(p.stdout) == run_fixture()
    assert p.stderr == ""
    assert "SYN-QUOTE-V1" not in p.stdout
    assert "99freelas" not in p.stdout
    assert_not_real(json.loads(p.stdout))


def test_unknown_schema_or_real_data_is_not_treated_as_an_exercise() -> None:
    for change in (
        {"kind": "real_customer"},
        {"schema_version": 2},
        {"tenant_ref": "real-tenant"},
        {"opportunity_ref": "99freelas-project-123"},
        {"billing_trigger": "auto"},
        {"added_external_url": "https://example.invalid"},
    ):
        case = scenario()
        case.update(change)
        result = assess_scenario(case)
        assert result["simulation_result"] == "blocked"
        assert_not_real(result)


@pytest.mark.parametrize("value", [None, {}, [], 0, "not a scenario"])
def test_invalid_scenario_shape_blocks(value: object) -> None:
    result = assess_scenario(value)
    assert result["blocking_codes"] == ["scenario_schema_invalid"]
    assert_not_real(result)


@pytest.mark.parametrize("gate", ["G0", "G1", "G4a", "G4b", "G5", "G6", "G7", "G8", "G9", "G10"])
def test_missing_gate_never_completes_scenario(gate: str) -> None:
    case = scenario()
    case["events"] = [event for event in case["events"] if event["gate"] != gate]
    result = assess_scenario(case)
    assert result["simulation_result"] == "blocked"
    assert result["blocking_codes"]
    assert_not_real(result)


def test_cannot_send_without_exact_human_authorization_gate() -> None:
    case = scenario()
    case["events"].pop(4)
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["prerequisite_missing"]
    assert result["blocked_at"] == "G4b"
    assert_not_real(result)


@pytest.mark.parametrize("gate", ["G4a", "G4b", "G5"])
def test_any_proposal_version_change_invalidates_downstream_gate(gate: str) -> None:
    case = scenario()
    edit_gate(case, gate)["version"] = "SYN-QUOTE-V2"
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["version_mismatch"]
    assert result["blocked_at"] == gate
    assert_not_real(result)


@pytest.mark.parametrize("gate", ["G7", "G9"])
def test_delivery_and_receivable_versions_must_match_upstream(gate: str) -> None:
    case = scenario()
    edit_gate(case, gate)["version"] = "SYN-CONFLICT-V2"
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["version_mismatch"]
    assert_not_real(result)


def test_payment_requires_financial_actor_not_delivery_actor() -> None:
    case = scenario()
    edit_gate(case, "G9")["actor"] = "technical"
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["wrong_actor"]
    assert result["blocked_at"] == "G9"
    assert_not_real(result)


def test_unverifiable_or_reused_reference_rejected_without_echo() -> None:
    case = scenario()
    edit_gate(case, "G4a")["evidence_ref"] = "private-client-key"
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["unverifiable_synthetic_reference"]
    assert "private-client-key" not in str(result)
    assert_not_real(result)

    case = scenario()
    edit_gate(case, "G4b")["evidence_ref"] = edit_gate(case, "G4a")["evidence_ref"]
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["repeated_evidence_reference"]
    assert_not_real(result)


@pytest.mark.parametrize("gate", ["G2", "G3", "G9"])
def test_uncertain_remote_result_blocks_and_never_automatically_retries(gate: str) -> None:
    case = scenario()
    edit_gate(case, gate)["outcome"] = "unknown"
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["unresolved_remote_outcome"]
    assert result["blocked_at"] == gate
    assert_not_real(result)


def test_partial_payment_does_not_count_as_completed_receipt() -> None:
    case = scenario()
    case["events"] = [
        event for event in case["events"]
        if not (event["gate"] == "G9" and event["outcome"] == "settled")
    ]
    result = assess_scenario(case)
    assert result["simulation_result"] == "blocked"
    assert result["finance_projection"] == "simulated_partial"
    assert result["blocking_codes"] == ["finance_not_settled"]
    assert_not_real(result)


@pytest.mark.parametrize("outcome", ["reversed", "overdue"])
def test_reversal_or_overdue_payment_blocks(outcome: str) -> None:
    case = scenario()
    edit_gate(case, "G9")["outcome"] = outcome
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["finance_not_settled"]
    assert_not_real(result)


def test_duplicated_payment_reconciliation_cannot_be_claimed_twice() -> None:
    case = scenario()
    duplicate = deepcopy(edit_gate(case, "G9", occurrence=1))
    duplicate["evidence_ref"] = "SYN-BANK-SETTLED-EXTRA"
    case["events"].insert(-1, duplicate)
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["invalid_finance_reconciliation"]
    assert_not_real(result)


def test_duplicate_send_is_rejected_even_if_evidence_is_different() -> None:
    case = scenario()
    send = deepcopy(edit_gate(case, "G4b"))
    send["evidence_ref"] = "SYN-OTHER-SEND-001"
    case["events"].insert(6, send)
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["duplicate_gate"]
    assert_not_real(result)


def test_upfront_invoice_can_be_simulated_before_delivery() -> None:
    case = scenario()
    case["billing_trigger"] = "upfront"
    events = case["events"]
    early_invoice = [event for event in events if event["gate"] in ("G8", "G9")]
    events = [event for event in events if event["gate"] not in ("G8", "G9")]
    insert = next(i for i, event in enumerate(events) if event["gate"] == "G6")
    events[insert:insert] = early_invoice
    case["events"] = events
    result = assess_scenario(case)
    assert result["simulation_result"] == "simulated_sequence_complete"
    assert_not_real(result)


@pytest.mark.parametrize("trigger", ["upfront", "milestone", "after_delivery"])
def test_billing_cannot_happen_before_its_contract_trigger(trigger: str) -> None:
    case = scenario()
    case["billing_trigger"] = trigger
    events = case["events"]
    invoice = next(event for event in events if event["gate"] == "G8")
    events.remove(invoice)
    # The trigger for "upfront" (G5) is not yet reached at this insertion.
    index = {"upfront": 5, "milestone": 7, "after_delivery": 8}[trigger]
    events.insert(index, invoice)
    result = assess_scenario(case)
    assert result["simulation_result"] == "blocked"
    assert result["blocking_codes"] == (
        ["prerequisite_missing"] if trigger == "upfront"
        else ["billing_trigger_not_met"]
    )
    assert_not_real(result)


def test_support_may_be_recorded_after_delivery_before_finance_is_settled() -> None:
    case = scenario()
    # Human support may begin despite incomplete payment, but this alone
    # does not make the rehearsal successful or the invoice paid.
    case["events"] = [
        event for event in case["events"] if
        not (event["gate"] == "G9" and event["outcome"] == "settled")
    ]
    result = assess_scenario(case)
    assert "G10" in result["completed_simulated_gates"]
    assert result["blocking_codes"] == ["finance_not_settled"]
    assert_not_real(result)


def test_extra_event_fields_or_unsanctioned_actions_are_not_allowed() -> None:
    case = scenario()
    edit_gate(case, "G4b")["send_to_client"] = True
    result = assess_scenario(case)
    assert result["blocking_codes"] == ["event_schema_invalid"]
    assert_not_real(result)


def test_no_network_database_or_deployment_hooks_in_rehearsal() -> None:
    content = (Path(__file__).resolve().parents[1] / "operations/rehearsal.py").read_text()
    banned = ("import socket", "import httpx", "import requests", "import sqlalchemy",
              "urllib.request", "subprocess.", "os.system(", "post(", "publish(")
    for token in banned:
        assert token not in content
    assert len(LIVE_GAPS) >= 7
    assert set(BILLING) == {"upfront", "milestone", "after_delivery"}

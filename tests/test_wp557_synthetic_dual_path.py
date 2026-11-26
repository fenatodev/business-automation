"""WP-557: bounded offline rehearsal for synthetic commercial paths."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import subprocess
import sys

import pytest

from operations.autonomy_simulation import (
    SimulationInputError,
    advance_to,
    load_scenario,
    new_state,
    restore_checkpoint,
    run_scenario,
    serialize_checkpoint,
    validate_scenario,
)


def test_72_hour_rehearsal_exercises_both_routes_and_reports_only_simulation() -> None:
    _, report = run_scenario()

    assert report["kind"] == "synthetic_dual_path_72h_rehearsal"
    assert report["simulation_only"] is True
    assert report["duration_hours"] == 72
    assert report["checkpoint_restored"] is True
    assert report["subjects_total"] == 8
    assert report["routes"] == {"recovery": 4, "inbound": 4}
    assert report["simulated_contact_actions"] == 6
    assert report["real_messages_sent"] == 0
    assert report["external_actions_taken"] is False
    assert report["external_api_calls"] == 0
    assert report["external_cost_usd"] == 0
    assert report["production_enforcement_proven"] is False
    assert report["commercial_success"] is False
    assert report["f2_exit_met"] is False


def test_permission_opt_out_human_review_limit_and_retry_paths_are_exercised() -> None:
    _, report = run_scenario()

    assert report["permission_blocks"] == 2
    assert report["opt_out_blocks"] == 1
    assert report["human_review_blocks"] == 3
    assert report["contact_limit_blocks"] == 3
    assert report["injected_failures"] == 2
    assert report["recovered_retries"] == 2
    assert report["duplicate_events_suppressed"] == 2


def test_checkpoint_restore_matches_a_single_continuous_run() -> None:
    scenario = load_scenario()
    split = new_state(scenario)
    advance_to(split, scenario, scenario["checkpoint_hour"])
    restored = restore_checkpoint(serialize_checkpoint(split), scenario)
    advance_to(restored, scenario, scenario["duration_hours"])

    continuous = new_state(scenario)
    advance_to(continuous, scenario, scenario["duration_hours"])

    assert serialize_checkpoint(restored) == serialize_checkpoint(continuous)


def test_duplicate_event_id_is_scoped_to_tenant_and_never_duplicates_action() -> None:
    state, report = run_scenario()
    cross_tenant_actions = {
        (action["tenant_ref"], action["event_id"])
        for action in state["simulated_actions"]
        if action["event_id"] == "SYN-EVT-CROSS-TENANT"
    }

    assert cross_tenant_actions == {
        ("SYN-TENANT-A", "SYN-EVT-CROSS-TENANT"),
        ("SYN-TENANT-B", "SYN-EVT-CROSS-TENANT"),
    }
    action_keys = [
        (action["tenant_ref"], action["event_id"])
        for action in state["simulated_actions"]
    ]
    assert len(action_keys) == len(set(action_keys))
    assert report["tenant_isolation_preserved"] is True


def test_every_recorded_state_transition_has_one_tenant_scoped_audit_entry() -> None:
    state, report = run_scenario()

    assert report["state_transitions"] == report["audit_entries"] == len(state["audit"])
    assert report["audit_complete"] is True
    assert report["tenant_isolation_preserved"] is True
    assert all(
        entry["from_status"] != entry["to_status"]
        or entry["contact_count_before"] != entry["contact_count_after"]
        for entry in state["audit"]
    )
    assert all(entry["simulated_at"].endswith("+00:00") for entry in state["audit"])


def test_each_simulated_contact_has_permission_limit_and_matching_audit() -> None:
    state, report = run_scenario()
    audit_actions = {
        (entry["tenant_ref"], entry["opportunity_ref"], entry["event_id"])
        for entry in state["audit"]
        if entry["outcome"] in {"simulated_inbound_reply", "simulated_followup"}
    }

    assert report["all_simulated_actions_authorized"] is True
    assert report["contact_limits_respected"] is True
    assert all(
        state["subjects"][f"{action['tenant_ref']}::{action['opportunity_ref']}"]
        ["contact_permission"]
        for action in state["simulated_actions"]
    )
    assert all(
        (action["tenant_ref"], action["opportunity_ref"], action["event_id"]) in audit_actions
        for action in state["simulated_actions"]
    )


def test_opt_out_remains_terminal_when_later_handoff_event_arrives() -> None:
    scenario = deepcopy(load_scenario())
    scenario["events"].insert(8, {
        "event_id": "SYN-EVT-A-003-HANDOFF-AFTER-OPT-OUT",
        "tenant_ref": "SYN-TENANT-A",
        "opportunity_ref": "SYN-OPP-A-003",
        "at_hour": 18,
        "kind": "human_handoff",
    })
    state = new_state(scenario)
    advance_to(state, scenario, scenario["duration_hours"])

    assert state["subjects"]["SYN-TENANT-A::SYN-OPP-A-003"]["status"] == "opted_out"
    assert state["metrics"]["opt_out_blocks"] == 2


def test_human_handoff_blocks_all_later_contact_attempts() -> None:
    scenario = deepcopy(load_scenario())
    scenario["events"].append({
        "event_id": "SYN-EVT-B-001-HUMAN-HANDOFF",
        "tenant_ref": "SYN-TENANT-B",
        "opportunity_ref": "SYN-OPP-B-001",
        "at_hour": 12,
        "kind": "human_handoff",
    })
    scenario["events"].sort(key=lambda event: event["at_hour"])
    state, report = run_scenario(scenario)
    inbound_actions = [
        action for action in state["simulated_actions"]
        if action["tenant_ref"] == "SYN-TENANT-B"
        and action["opportunity_ref"] == "SYN-OPP-B-001"
    ]

    assert [action["at_hour"] for action in inbound_actions] == [0]
    assert state["subjects"]["SYN-TENANT-B::SYN-OPP-B-001"]["status"] == "human_review"
    assert report["all_simulated_actions_authorized"] is True


@pytest.mark.parametrize(
    ("mutate", "error"),
    [
        (lambda value: value.update(scenario_ref="real-account"), "scenario_ref_not_synthetic"),
        (lambda value: value.update(subjects=value["subjects"][:5]), "subject_count_out_of_bounds"),
        (
            lambda value: value["events"][0].update(
                synthetic_message="Olá, sou uma mensagem real"
            ),
            "inbound_message_not_synthetic",
        ),
        (
            lambda value: value["events"][0].update(at_hour=73),
            "event_hour_invalid",
        ),
    ],
)
def test_malformed_or_non_synthetic_scenarios_are_rejected(mutate, error: str) -> None:
    scenario = deepcopy(load_scenario())
    mutate(scenario)

    with pytest.raises(SimulationInputError, match=error):
        validate_scenario(scenario)


def test_checkpoint_rejects_foreign_or_tampered_state() -> None:
    scenario = load_scenario()
    state = new_state(scenario)
    advance_to(state, scenario, scenario["checkpoint_hour"])
    checkpoint = json.loads(serialize_checkpoint(state))
    checkpoint["metrics"]["state_transitions"] += 1

    with pytest.raises(SimulationInputError, match="checkpoint_state_invalid"):
        restore_checkpoint(json.dumps(checkpoint), scenario)

    with pytest.raises(SimulationInputError, match="checkpoint_incompatible"):
        restore_checkpoint(serialize_checkpoint(state), {
            **scenario,
            "scenario_ref": "SYN-OTHER-SCENARIO",
        })


def test_clock_is_derived_from_fixture_not_wall_time() -> None:
    state, _ = run_scenario()
    action = next(
        item for item in state["simulated_actions"]
        if item["tenant_ref"] == "SYN-TENANT-A"
        and item["event_id"] == "SYN-EVT-CROSS-TENANT"
    )
    start = datetime.fromisoformat(load_scenario()["start_at"].replace("Z", "+00:00"))

    assert action["simulated_at"] == (start + timedelta(hours=24)).isoformat()


def test_cli_emits_sanitized_machine_readable_report() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "operations.autonomy_simulation", "--run"],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        check=True,
        text=True,
    )
    report = json.loads(result.stdout)

    assert result.stderr == ""
    assert "SYNTHETIC:" not in result.stdout
    assert report["simulation_only"] is True
    assert report["external_actions_taken"] is False
    assert report["f2_exit_met"] is False
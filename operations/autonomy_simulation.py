"""Offline, synthetic rehearsal for the two commercial automation paths.

This reference simulator never calls the application, a channel provider, or an
external service. Its output is evidence about this scenario only, not about
production enforcement or commercial readiness.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta
import json
from pathlib import Path
import re
from typing import Any


FIXTURE = Path(__file__).with_name("fixtures") / "wp557-dual-path-72h.json"
_SYNTHETIC_REF = re.compile(r"SYN-[A-Z0-9]+(?:-[A-Z0-9]+)*", flags=re.ASCII)
_SUBJECT_FIELDS = {
    "tenant_ref", "opportunity_ref", "route", "channel",
    "contact_permission", "human_review_required",
}
_EVENT_FIELDS = {
    "event_id", "tenant_ref", "opportunity_ref", "at_hour", "kind",
}
_EVENT_KINDS = {"followup_due", "inbound_received", "opt_out", "human_handoff"}


class SimulationInputError(ValueError):
    """Raised when a scenario is malformed or contains non-synthetic refs."""


def _is_synthetic_ref(value: Any) -> bool:
    return isinstance(value, str) and _SYNTHETIC_REF.fullmatch(value) is not None


def validate_scenario(scenario: Any) -> dict[str, Any]:
    """Validate the bounded fixture shape before processing any event."""
    required = {
        "schema_version", "scenario_ref", "start_at", "duration_hours",
        "checkpoint_hour", "policy", "subjects", "events",
    }
    if not isinstance(scenario, dict) or set(scenario) != required:
        raise SimulationInputError("scenario_schema_invalid")
    if type(scenario["schema_version"]) is not int or scenario["schema_version"] != 1:
        raise SimulationInputError("scenario_version_unsupported")
    if not _is_synthetic_ref(scenario["scenario_ref"]):
        raise SimulationInputError("scenario_ref_not_synthetic")
    if type(scenario["duration_hours"]) is not int or not 1 <= scenario["duration_hours"] <= 72:
        raise SimulationInputError("duration_out_of_bounds")
    if (
        type(scenario["checkpoint_hour"]) is not int
        or not 0 < scenario["checkpoint_hour"] < scenario["duration_hours"]
    ):
        raise SimulationInputError("checkpoint_out_of_bounds")

    try:
        start_at = datetime.fromisoformat(scenario["start_at"].replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise SimulationInputError("start_at_invalid") from exc
    if start_at.tzinfo is None or start_at.utcoffset() != timedelta(0):
        raise SimulationInputError("start_at_must_be_utc")

    policy = scenario["policy"]
    if (
        not isinstance(policy, dict)
        or set(policy) != {"max_contacts_per_subject_channel"}
        or type(policy["max_contacts_per_subject_channel"]) is not int
        or policy["max_contacts_per_subject_channel"] < 1
    ):
        raise SimulationInputError("policy_invalid")

    subjects = scenario["subjects"]
    if not isinstance(subjects, list) or not 6 <= len(subjects) <= 12:
        raise SimulationInputError("subject_count_out_of_bounds")
    subject_keys: set[tuple[str, str]] = set()
    for subject in subjects:
        if not isinstance(subject, dict) or set(subject) != _SUBJECT_FIELDS:
            raise SimulationInputError("subject_schema_invalid")
        if not _is_synthetic_ref(subject["tenant_ref"]) or not _is_synthetic_ref(subject["opportunity_ref"]):
            raise SimulationInputError("subject_ref_not_synthetic")
        if not isinstance(subject["route"], str) or subject["route"] not in {"recovery", "inbound"}:
            raise SimulationInputError("route_invalid")
        if not isinstance(subject["channel"], str) or subject["channel"] not in {"email", "web"}:
            raise SimulationInputError("channel_invalid")
        if type(subject["contact_permission"]) is not bool:
            raise SimulationInputError("contact_permission_invalid")
        if type(subject["human_review_required"]) is not bool:
            raise SimulationInputError("human_review_required_invalid")
        key = (subject["tenant_ref"], subject["opportunity_ref"])
        if key in subject_keys:
            raise SimulationInputError("subject_ref_duplicate")
        subject_keys.add(key)

    events = scenario["events"]
    if not isinstance(events, list):
        raise SimulationInputError("events_invalid")
    previous_hour = -1
    for event in events:
        if not isinstance(event, dict) or set(event) - (_EVENT_FIELDS | {"fail_once", "synthetic_message"}):
            raise SimulationInputError("event_schema_invalid")
        if not _EVENT_FIELDS.issubset(event):
            raise SimulationInputError("event_schema_invalid")
        if not _is_synthetic_ref(event["event_id"]):
            raise SimulationInputError("event_id_not_synthetic")
        if (
            not _is_synthetic_ref(event["tenant_ref"])
            or not _is_synthetic_ref(event["opportunity_ref"])
        ):
            raise SimulationInputError("event_subject_ref_not_synthetic")
        if type(event["at_hour"]) is not int or not 0 <= event["at_hour"] <= scenario["duration_hours"]:
            raise SimulationInputError("event_hour_invalid")
        if event["at_hour"] < previous_hour:
            raise SimulationInputError("events_not_time_ordered")
        previous_hour = event["at_hour"]
        if not isinstance(event["kind"], str) or event["kind"] not in _EVENT_KINDS:
            raise SimulationInputError("event_kind_invalid")
        if "fail_once" in event and type(event["fail_once"]) is not bool:
            raise SimulationInputError("failure_flag_invalid")
        key = (event["tenant_ref"], event["opportunity_ref"])
        if key not in subject_keys:
            raise SimulationInputError("event_subject_unknown")
        subject = next(item for item in subjects if (item["tenant_ref"], item["opportunity_ref"]) == key)
        if event["kind"] == "inbound_received" and subject["route"] != "inbound":
            raise SimulationInputError("inbound_event_wrong_route")
        if event["kind"] == "inbound_received":
            message = event.get("synthetic_message")
            if not isinstance(message, str) or not message.startswith("SYNTHETIC: "):
                raise SimulationInputError("inbound_message_not_synthetic")
        elif "synthetic_message" in event:
            raise SimulationInputError("message_only_allowed_for_inbound")

    return scenario


def load_scenario(path: Path = FIXTURE) -> dict[str, Any]:
    """Load and validate the repository's synthetic, offline fixture."""
    return validate_scenario(json.loads(path.read_text(encoding="utf-8")))


def new_state(scenario: dict[str, Any]) -> dict[str, Any]:
    """Create an isolated run state after validating its synthetic fixture."""
    validate_scenario(scenario)
    subjects = {}
    for item in scenario["subjects"]:
        key = _subject_key(item["tenant_ref"], item["opportunity_ref"])
        subjects[key] = {
            **item,
            "status": "new",
            "contacts_by_channel": {},
            "opted_out": False,
        }
    return {
        "state_version": 1,
        "scenario_ref": scenario["scenario_ref"],
        "clock_hour": 0,
        "event_cursor": 0,
        "subjects": subjects,
        "processed_event_keys": [],
        "failed_event_keys": [],
        "audit": [],
        "simulated_actions": [],
        "metrics": {
            "duplicate_events_suppressed": 0,
            "permission_blocks": 0,
            "opt_out_blocks": 0,
            "human_review_blocks": 0,
            "contact_limit_blocks": 0,
            "injected_failures": 0,
            "recovered_retries": 0,
            "state_transitions": 0,
        },
    }


def _subject_key(tenant_ref: str, opportunity_ref: str) -> str:
    return f"{tenant_ref}::{opportunity_ref}"


def serialize_checkpoint(state: dict[str, Any]) -> str:
    """Return a deterministic JSON checkpoint suitable for a restart test."""
    return json.dumps(state, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def restore_checkpoint(checkpoint: str, scenario: dict[str, Any]) -> dict[str, Any]:
    """Restore a compatible checkpoint and reject malformed or foreign state."""
    try:
        state = json.loads(checkpoint)
    except (TypeError, json.JSONDecodeError) as exc:
        raise SimulationInputError("checkpoint_invalid") from exc
    if (
        not isinstance(state, dict)
        or state.get("state_version") != 1
        or state.get("scenario_ref") != scenario["scenario_ref"]
        or type(state.get("event_cursor")) is not int
        or not 0 <= state["event_cursor"] <= len(scenario["events"])
        or type(state.get("clock_hour")) is not int
        or not 0 <= state["clock_hour"] <= scenario["duration_hours"]
        or not isinstance(state.get("subjects"), dict)
        or set(state["subjects"]) != {
            _subject_key(item["tenant_ref"], item["opportunity_ref"])
            for item in scenario["subjects"]
        }
    ):
        raise SimulationInputError("checkpoint_incompatible")
    expected_metrics = {
        "duplicate_events_suppressed", "permission_blocks", "opt_out_blocks",
        "human_review_blocks", "contact_limit_blocks", "injected_failures",
        "recovered_retries", "state_transitions",
    }
    if (
        not isinstance(state.get("metrics"), dict)
        or set(state["metrics"]) != expected_metrics
        or any(type(value) is not int or value < 0 for value in state["metrics"].values())
        or not isinstance(state.get("audit"), list)
        or not isinstance(state.get("simulated_actions"), list)
        or not isinstance(state.get("processed_event_keys"), list)
        or not isinstance(state.get("failed_event_keys"), list)
        or state["metrics"]["state_transitions"] != len(state["audit"])
    ):
        raise SimulationInputError("checkpoint_state_invalid")
    scenario_subjects = {
        _subject_key(item["tenant_ref"], item["opportunity_ref"]): item
        for item in scenario["subjects"]
    }
    for key, subject in state["subjects"].items():
        original = scenario_subjects[key]
        if (
            not isinstance(subject, dict)
            or any(subject.get(field) != original[field] for field in _SUBJECT_FIELDS)
            or subject.get("status") not in {
                "new", "qualified", "contacted", "permission_blocked", "opted_out", "human_review",
            }
            or type(subject.get("opted_out")) is not bool
            or not isinstance(subject.get("contacts_by_channel"), dict)
            or any(
                type(count) is not int or count < 0
                for count in subject["contacts_by_channel"].values()
            )
        ):
            raise SimulationInputError("checkpoint_subject_invalid")
    return state


def _record_transition(
    state: dict[str, Any],
    subject: dict[str, Any],
    event: dict[str, Any],
    *,
    to_status: str,
    outcome: str,
    contact_delta: int = 0,
) -> None:
    from_status = subject["status"]
    channel = subject["channel"]
    contacts = subject["contacts_by_channel"].get(channel, 0)
    if to_status != from_status or contact_delta:
        subject["status"] = to_status
        if contact_delta:
            subject["contacts_by_channel"][channel] = contacts + contact_delta
        state["audit"].append({
            "at_hour": event["at_hour"],
            "simulated_at": event["simulated_at"],
            "tenant_ref": subject["tenant_ref"],
            "opportunity_ref": subject["opportunity_ref"],
            "event_id": event["event_id"],
            "from_status": from_status,
            "to_status": to_status,
            "contact_count_before": contacts,
            "contact_count_after": contacts + contact_delta,
            "outcome": outcome,
        })
        state["metrics"]["state_transitions"] += 1


def _process_event(
    state: dict[str, Any],
    event: dict[str, Any],
    policy: dict[str, Any],
    start_at: datetime,
) -> None:
    event_key = _subject_key(event["tenant_ref"], event["event_id"])
    processed = set(state["processed_event_keys"])
    if event_key in processed:
        state["metrics"]["duplicate_events_suppressed"] += 1
        return

    if event.get("fail_once"):
        state["metrics"]["injected_failures"] += 1
        if event_key not in state["failed_event_keys"]:
            state["failed_event_keys"].append(event_key)
        return

    subject = state["subjects"][_subject_key(event["tenant_ref"], event["opportunity_ref"])]
    event = {
        **event,
        "simulated_at": (start_at + timedelta(hours=event["at_hour"])).isoformat(),
    }
    if event_key in state["failed_event_keys"]:
        state["metrics"]["recovered_retries"] += 1

    kind = event["kind"]
    if kind == "opt_out":
        subject["opted_out"] = True
        _record_transition(state, subject, event, to_status="opted_out", outcome="opt_out_recorded")
    elif subject["opted_out"]:
        state["metrics"]["opt_out_blocks"] += 1
    elif (
        kind == "human_handoff"
        or subject["human_review_required"]
        or subject["status"] == "human_review"
    ):
        state["metrics"]["human_review_blocks"] += 1
        _record_transition(state, subject, event, to_status="human_review", outcome="human_review_required")
    elif kind in {"inbound_received", "followup_due"}:
        if not subject["contact_permission"]:
            state["metrics"]["permission_blocks"] += 1
            _record_transition(
                state, subject, event,
                to_status="permission_blocked", outcome="contact_permission_missing",
            )
        else:
            channel_count = subject["contacts_by_channel"].get(subject["channel"], 0)
            if channel_count >= policy["max_contacts_per_subject_channel"]:
                state["metrics"]["contact_limit_blocks"] += 1
            else:
                status = "qualified" if kind == "inbound_received" else "contacted"
                _record_transition(
                    state, subject, event,
                    to_status=status,
                    outcome="simulated_inbound_reply" if kind == "inbound_received" else "simulated_followup",
                    contact_delta=1,
                )
                state["simulated_actions"].append({
                    "at_hour": event["at_hour"],
                    "simulated_at": event["simulated_at"],
                    "tenant_ref": subject["tenant_ref"],
                    "opportunity_ref": subject["opportunity_ref"],
                    "event_id": event["event_id"],
                    "channel": subject["channel"],
                    "action": "simulated_contact",
                })

    state["processed_event_keys"].append(event_key)


def advance_to(
    state: dict[str, Any],
    scenario: dict[str, Any],
    through_hour: int,
) -> dict[str, Any]:
    """Advance the injected simulation clock and process due fixture events."""
    validate_scenario(scenario)
    if type(through_hour) is not int or not state["clock_hour"] <= through_hour <= scenario["duration_hours"]:
        raise SimulationInputError("clock_advance_invalid")
    events = scenario["events"]
    while (
        state["event_cursor"] < len(events)
        and events[state["event_cursor"]]["at_hour"] <= through_hour
    ):
        event = events[state["event_cursor"]]
        start_at = datetime.fromisoformat(scenario["start_at"].replace("Z", "+00:00"))
        _process_event(state, event, scenario["policy"], start_at)
        state["event_cursor"] += 1
    state["clock_hour"] = through_hour
    return state


def _report(state: dict[str, Any], scenario: dict[str, Any], *, checkpoint_restored: bool) -> dict[str, Any]:
    route_counts = Counter(item["route"] for item in scenario["subjects"])
    status_counts = Counter(item["status"] for item in state["subjects"].values())
    subjects = state["subjects"]
    audit_is_tenant_scoped = all(
        _subject_key(entry["tenant_ref"], entry["opportunity_ref"]) in subjects
        for entry in state["audit"]
    )
    max_contacts = scenario["policy"]["max_contacts_per_subject_channel"]
    limits_respected = all(
        count <= max_contacts
        for subject in subjects.values()
        for count in subject["contacts_by_channel"].values()
    )
    audit_actions = {
        (entry["tenant_ref"], entry["opportunity_ref"], entry["event_id"]): entry
        for entry in state["audit"]
        if entry["outcome"] in {"simulated_inbound_reply", "simulated_followup"}
    }
    audit_positions = {
        (entry["tenant_ref"], entry["opportunity_ref"], entry["event_id"]): index
        for index, entry in enumerate(state["audit"])
        if entry["outcome"] in {"simulated_inbound_reply", "simulated_followup"}
    }
    opt_out_positions = {}
    human_review_positions = {}
    for index, entry in enumerate(state["audit"]):
        subject_key = _subject_key(entry["tenant_ref"], entry["opportunity_ref"])
        if entry["outcome"] == "opt_out_recorded" and subject_key not in opt_out_positions:
            opt_out_positions[subject_key] = index
        if entry["outcome"] == "human_review_required" and subject_key not in human_review_positions:
            human_review_positions[subject_key] = index
    actions_authorized = all(
        subjects[_subject_key(action["tenant_ref"], action["opportunity_ref"])]
        ["contact_permission"]
        and not subjects[_subject_key(action["tenant_ref"], action["opportunity_ref"])]
        ["human_review_required"]
        and (action["tenant_ref"], action["opportunity_ref"], action["event_id"]) in audit_actions
        and audit_positions[(action["tenant_ref"], action["opportunity_ref"], action["event_id"])]
        < opt_out_positions.get(
            _subject_key(action["tenant_ref"], action["opportunity_ref"]), len(state["audit"])
        )
        and audit_positions[(action["tenant_ref"], action["opportunity_ref"], action["event_id"])]
        < human_review_positions.get(
            _subject_key(action["tenant_ref"], action["opportunity_ref"]), len(state["audit"])
        )
        for action in state["simulated_actions"]
    )
    return {
        "kind": "synthetic_dual_path_72h_rehearsal",
        "scenario_ref": scenario["scenario_ref"],
        "simulation_only": True,
        "duration_hours": scenario["duration_hours"],
        "checkpoint_restored": checkpoint_restored,
        "subjects_total": len(scenario["subjects"]),
        "routes": {key: route_counts[key] for key in ("recovery", "inbound")},
        "simulated_contact_actions": len(state["simulated_actions"]),
        "real_messages_sent": 0,
        "external_actions_taken": False,
        "external_api_calls": 0,
        "external_cost_usd": 0,
        "duplicate_events_suppressed": state["metrics"]["duplicate_events_suppressed"],
        "permission_blocks": state["metrics"]["permission_blocks"],
        "opt_out_blocks": state["metrics"]["opt_out_blocks"],
        "human_review_blocks": state["metrics"]["human_review_blocks"],
        "contact_limit_blocks": state["metrics"]["contact_limit_blocks"],
        "injected_failures": state["metrics"]["injected_failures"],
        "recovered_retries": state["metrics"]["recovered_retries"],
        "state_transitions": state["metrics"]["state_transitions"],
        "audit_entries": len(state["audit"]),
        "audit_complete": state["metrics"]["state_transitions"] == len(state["audit"]),
        "tenant_isolation_preserved": audit_is_tenant_scoped,
        "contact_limits_respected": limits_respected,
        "all_simulated_actions_authorized": actions_authorized,
        "final_status_counts": {key: status_counts[key] for key in sorted(status_counts)},
        "production_enforcement_proven": False,
        "commercial_success": False,
        "f2_exit_met": False,
    }


def run_scenario(scenario: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Run once continuously and once across a serialized mid-run restart."""
    scenario = validate_scenario(scenario if scenario is not None else load_scenario())
    split_state = new_state(scenario)
    advance_to(split_state, scenario, scenario["checkpoint_hour"])
    checkpoint = serialize_checkpoint(split_state)
    restored_state = restore_checkpoint(checkpoint, scenario)
    advance_to(restored_state, scenario, scenario["duration_hours"])

    continuous_state = new_state(scenario)
    advance_to(continuous_state, scenario, scenario["duration_hours"])
    if serialize_checkpoint(restored_state) != serialize_checkpoint(continuous_state):
        raise RuntimeError("checkpoint_recovery_not_deterministic")
    return restored_state, _report(restored_state, scenario, checkpoint_restored=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the offline WP-557 synthetic rehearsal.")
    parser.add_argument("--run", action="store_true", help="run the bundled synthetic scenario")
    args = parser.parse_args()
    if not args.run:
        parser.error("--run is required")
    _, report = run_scenario()
    print(json.dumps(report, ensure_ascii=True, sort_keys=True))


if __name__ == "__main__":
    main()
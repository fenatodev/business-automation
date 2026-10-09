"""WP-020: all tests are synthetic, offline, and independent of the API DB."""

import json
import subprocess
import sys

import pytest

from examples.order_to_crm import DemoBridge, FakeCRM, parse_notice, run_demo


def test_created_duplicate_conflict_preserve_original() -> None:
    crm = FakeCRM()
    bridge = DemoBridge(crm)
    first = {"order_ref": "ORD-101", "customer_ref": "CUST-001"}
    changed = {"order_ref": "ORD-101", "customer_ref": "CUST-002"}

    assert bridge.handle(first)["status"] == "created"
    assert bridge.handle(first)["status"] == "duplicate"
    assert bridge.handle(changed)["status"] == "conflict"
    assert crm.records == {"ORD-101": "CUST-001"}
    assert crm.write_count == 1


@pytest.mark.parametrize(
    "payload",
    [
        None,
        [],
        {},
        {"order_ref": "ORD-101"},
        {"order_ref": "ORD-101", "customer_ref": "CUST-001", "extra": True},
        {"order_ref": "ord-101", "customer_ref": "CUST-001"},
        {"order_ref": "", "customer_ref": "CUST-001"},
        {"order_ref": "ORD-101", "customer_ref": 123},
        {"order_ref": "ORD-101", "customer_ref": "not-synthetic@example.invalid"},
    ],
)
def test_invalid_notice_is_rejected_without_logging_payload(payload: object) -> None:
    crm = FakeCRM()
    bridge = DemoBridge(crm)

    assert bridge.handle(payload) == {"status": "rejected", "reason": "invalid_fields"}
    assert crm.records == {}
    assert crm.write_count == 0


def test_parser_uses_only_explicit_synthetic_fields() -> None:
    order = parse_notice({"order_ref": "ORD-101", "customer_ref": "CUST-001"})
    assert order.order_ref == "ORD-101"
    assert order.customer_ref == "CUST-001"


def test_ambiguous_after_write_requires_positive_reconciliation() -> None:
    crm = FakeCRM(ambiguous_after_write={"ORD-202"})
    bridge = DemoBridge(crm)
    item = {"order_ref": "ORD-202", "customer_ref": "CUST-002"}

    assert bridge.handle(item)["status"] == "unknown"
    assert crm.write_count == 1
    assert bridge.handle(item)["status"] == "blocked"
    assert bridge.handle({"order_ref": "ORD-202", "customer_ref": "CUST-003"})["status"] == "blocked"
    assert crm.write_count == 1
    assert bridge.pending_unknown == ("ORD-202",)

    assert bridge.reconcile("ORD-202") == "reconciled"
    assert bridge.pending_unknown == ()
    assert bridge.handle(item)["status"] == "duplicate"
    assert crm.write_count == 1


def test_ambiguous_before_write_is_not_blindly_retried() -> None:
    crm = FakeCRM(ambiguous_before_write={"ORD-404"})
    bridge = DemoBridge(crm)
    item = {"order_ref": "ORD-404", "customer_ref": "CUST-004"}

    assert bridge.handle(item)["status"] == "unknown"
    assert bridge.reconcile("ORD-404") == "unresolved"
    assert bridge.handle(item)["status"] == "blocked"
    assert crm.write_count == 0
    assert crm.records == {}
    assert bridge.pending_unknown == ("ORD-404",)


def test_nonmatching_readback_does_not_release_unknown() -> None:
    crm = FakeCRM(ambiguous_before_write={"ORD-404"})
    bridge = DemoBridge(crm)
    item = {"order_ref": "ORD-404", "customer_ref": "CUST-004"}

    assert bridge.handle(item)["status"] == "unknown"
    crm.records["ORD-404"] = "CUST-999"
    assert bridge.reconcile("ORD-404") == "unresolved"
    assert bridge.handle(item)["status"] == "blocked"
    assert bridge.pending_unknown == ("ORD-404",)


def test_unrelated_order_can_continue_while_other_is_unknown() -> None:
    crm = FakeCRM(ambiguous_after_write={"ORD-202"})
    bridge = DemoBridge(crm)
    assert bridge.handle({"order_ref": "ORD-202", "customer_ref": "CUST-002"})["status"] == "unknown"
    assert bridge.handle({"order_ref": "ORD-303", "customer_ref": "CUST-003"})["status"] == "created"
    assert bridge.pending_unknown == ("ORD-202",)
    assert crm.write_count == 2


def test_full_demo_is_deterministic_and_honestly_labeled() -> None:
    a = run_demo()
    assert a == run_demo()
    assert a["kind"] == "synthetic_offline_demonstration"
    assert a["offer_reference"] == "client0-integration-flow-v1"
    assert [step["status"] for step in a["steps"]] == [
        "created",
        "duplicate",
        "conflict",
        "rejected",
        "unknown",
        "blocked",
        "unknown",
        "blocked",
        "created",
    ]
    assert a["reconciliation"] == {"after_write": "reconciled", "before_write": "unresolved"}
    assert a["after_positive_reconciliation"]["status"] == "duplicate"
    assert a["pending_unknown"] == ["ORD-404"]
    assert a["remote_writes"] == 3
    assert a["synthetic_crm_records"] == {
        "ORD-101": "CUST-001",
        "ORD-202": "CUST-002",
        "ORD-303": "CUST-003",
    }


def test_cli_runs_in_a_fresh_process_without_server_or_database() -> None:
    run = subprocess.run(
        [sys.executable, "-m", "examples.order_to_crm"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(run.stdout) == run_demo()
    assert run.stderr == ""

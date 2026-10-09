"""WP-020: offline, synthetic demonstration of one order-notice → CRM flow.

This is a teaching/portfolio fixture, not the production Business Automation
connector. No network, persistence, tenant identity, real provider or credentials.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass


_ORDER_PATTERN = re.compile(r"ORD-[0-9]{3}", flags=re.ASCII)
_CUSTOMER_PATTERN = re.compile(r"CUST-[0-9]{3}", flags=re.ASCII)


class InvalidNotice(ValueError):
    """An incoming notice does not match the synthetic contract."""


class RemoteConflict(Exception):
    """An order reference exists with a different customer reference."""


@dataclass(frozen=True)
class Notice:
    order_ref: str
    customer_ref: str


def parse_notice(payload: object) -> Notice:
    """Accept exactly two synthetic identifiers; never print rejected input."""
    if not isinstance(payload, dict) or set(payload) != {"order_ref", "customer_ref"}:
        raise InvalidNotice("invalid_fields")
    order_ref = payload["order_ref"]
    customer_ref = payload["customer_ref"]
    if not isinstance(order_ref, str) or _ORDER_PATTERN.fullmatch(order_ref) is None:
        raise InvalidNotice("invalid_order_ref")
    if not isinstance(customer_ref, str) or _CUSTOMER_PATTERN.fullmatch(customer_ref) is None:
        raise InvalidNotice("invalid_customer_ref")
    return Notice(order_ref=order_ref, customer_ref=customer_ref)


class FakeCRM:
    """An ephemeral deterministic destination with injected uncertain outcomes."""

    def __init__(
        self,
        *,
        ambiguous_before_write: set[str] | None = None,
        ambiguous_after_write: set[str] | None = None,
    ) -> None:
        self.records: dict[str, str] = {}
        self.write_count = 0
        self._before = set(ambiguous_before_write or ())
        self._after = set(ambiguous_after_write or ())

    def ensure(self, notice: Notice) -> str:
        """A result may be unknown even when the remote write occurred."""
        if notice.order_ref in self._before:
            self._before.remove(notice.order_ref)
            raise TimeoutError("outcome_unknown")

        existing = self.records.get(notice.order_ref)
        if existing is not None:
            if existing == notice.customer_ref:
                return "duplicate"
            raise RemoteConflict("conflicting_reference")

        self.records[notice.order_ref] = notice.customer_ref
        self.write_count += 1
        if notice.order_ref in self._after:
            self._after.remove(notice.order_ref)
            raise TimeoutError("outcome_unknown")
        return "created"

    def inspect(self, order_ref: str) -> str | None:
        """Simulate an explicit read-back, not proof of a real API result."""
        return self.records.get(order_ref)


class DemoBridge:
    """One in-memory flow: validate, ensure, block ambiguity, reconcile."""

    def __init__(self, crm: FakeCRM) -> None:
        self.crm = crm
        self._unknown: dict[str, Notice] = {}

    def handle(self, payload: object) -> dict[str, str]:
        try:
            notice = parse_notice(payload)
        except InvalidNotice:
            return {"status": "rejected", "reason": "invalid_fields"}

        if notice.order_ref in self._unknown:
            # Never blindly retry any command whose earlier outcome is unknown.
            return {"order_ref": notice.order_ref, "status": "blocked"}

        try:
            state = self.crm.ensure(notice)
        except RemoteConflict:
            state = "conflict"
        except TimeoutError:
            self._unknown[notice.order_ref] = notice
            state = "unknown"
        return {"order_ref": notice.order_ref, "status": state}

    def reconcile(self, order_ref: str) -> str:
        """Only positive matching read-back resolves an uncertain command."""
        notice = self._unknown.get(order_ref)
        if notice is None:
            return "not_pending"
        observed = self.crm.inspect(order_ref)
        if observed is None or observed != notice.customer_ref:
            return "unresolved"
        del self._unknown[order_ref]
        return "reconciled"

    @property
    def pending_unknown(self) -> tuple[str, ...]:
        return tuple(sorted(self._unknown))


def run_demo() -> dict[str, object]:
    """Reproducible result with exclusively invented references."""
    crm = FakeCRM(
        ambiguous_before_write={"ORD-404"},
        ambiguous_after_write={"ORD-202"},
    )
    bridge = DemoBridge(crm)
    events: list[object] = [
        {"order_ref": "ORD-101", "customer_ref": "CUST-001"},
        {"order_ref": "ORD-101", "customer_ref": "CUST-001"},
        {"order_ref": "ORD-101", "customer_ref": "CUST-009"},
        {"order_ref": "", "customer_ref": "CUST-002"},
        {"order_ref": "ORD-202", "customer_ref": "CUST-002"},
        {"order_ref": "ORD-202", "customer_ref": "CUST-002"},
        {"order_ref": "ORD-404", "customer_ref": "CUST-004"},
        {"order_ref": "ORD-404", "customer_ref": "CUST-004"},
        {"order_ref": "ORD-303", "customer_ref": "CUST-003"},
    ]
    steps = [bridge.handle(event) for event in events]
    reconciliation = {
        "after_write": bridge.reconcile("ORD-202"),
        "before_write": bridge.reconcile("ORD-404"),
    }
    after_review = bridge.handle({"order_ref": "ORD-202", "customer_ref": "CUST-002"})
    return {
        "kind": "synthetic_offline_demonstration",
        "offer_reference": "client0-integration-flow-v1",
        "steps": steps,
        "reconciliation": reconciliation,
        "after_positive_reconciliation": after_review,
        "pending_unknown": list(bridge.pending_unknown),
        "remote_writes": crm.write_count,
        "synthetic_crm_records": dict(sorted(crm.records.items())),
        "limitations": (
            "In-memory only; no API, database, tenant auth, durable jobs, "
            "cross-process replay guarantee, customer result or commercial proof."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), ensure_ascii=False, indent=2, sort_keys=True))

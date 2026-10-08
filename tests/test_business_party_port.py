"""WP-016: contrato/fake do ERP, sem HTTP, Docker, migrations ou efeitos externos."""

import pytest

from app.services.business_party_port import (
    BusinessPartyConflict,
    BusinessPartyKey,
    BusinessPartyOutcomeUnknown,
    BusinessPartyPort,
    BusinessPartyRejected,
    BusinessPartyRequest,
    BusinessPartyUnavailable,
)
from app.services.fake_business_party import FakeBusinessPartyPort


def make_request(
    *, company_id=1, connection_ref="erpnext-instance-a",
    customer_id=10, display_name="Empresa Ficticia",
):
    return BusinessPartyRequest(
        key=BusinessPartyKey(
            company_id=company_id,
            connection_ref=connection_ref,
            customer_id=customer_id,
        ),
        display_name=display_name,
    )


def test_replay_returns_exact_same_reference_without_second_create():
    port = FakeBusinessPartyPort()
    assert isinstance(port, BusinessPartyPort)
    command = make_request()
    first = port.ensure_business_party(command)
    second = port.ensure_business_party(command)
    assert first == second
    assert first.key == command.key
    assert first.remote_id.startswith("FAKE-PARTY-")
    assert port.created_count == 1


def test_changed_payload_requires_review_and_keeps_original():
    port = FakeBusinessPartyPort()
    original = make_request()
    remote_ref = port.ensure_business_party(original)
    modified = make_request(display_name="Outro nome hipotetico")

    with pytest.raises(BusinessPartyConflict):
        port.ensure_business_party(modified)

    assert port.inspect_synthetic_remote(original.key) == remote_ref
    assert port.created_count == 1


def test_equal_display_names_never_become_identity():
    port = FakeBusinessPartyPort()
    first = port.ensure_business_party(make_request(customer_id=10))
    second = port.ensure_business_party(make_request(customer_id=11))
    assert first.remote_id != second.remote_id
    assert port.created_count == 2


@pytest.mark.parametrize(
    "other",
    [
        make_request(company_id=2),
        make_request(connection_ref="erpnext-instance-b"),
    ],
    ids=["other-tenant", "other-connection"],
)
def test_key_is_isolated_by_tenant_and_connection(other):
    port = FakeBusinessPartyPort()
    first = port.ensure_business_party(make_request())
    second = port.ensure_business_party(other)
    assert first.remote_id != second.remote_id
    assert first.key != second.key
    assert port.created_count == 2


@pytest.mark.parametrize(
    "outcome,reason",
    [("reject_validation", "validation"), ("reject_permission", "permission")],
)
def test_rejections_do_not_create_remote_state(outcome, reason):
    port = FakeBusinessPartyPort()
    command = make_request()
    port.plan_next_outcome(command.key, outcome)

    with pytest.raises(BusinessPartyRejected) as error:
        port.ensure_business_party(command)

    assert error.value.reason == reason
    assert port.created_count == 0


def test_unavailability_before_write_does_not_create_state():
    port = FakeBusinessPartyPort()
    command = make_request()
    port.plan_next_outcome(command.key, "unavailable")
    with pytest.raises(BusinessPartyUnavailable):
        port.ensure_business_party(command)
    assert port.created_count == 0
    # Any future retry must be governed by a caller; fake never loops itself.


def test_unknown_before_write_blocks_blind_retry_even_if_lookup_empty():
    port = FakeBusinessPartyPort()
    command = make_request()
    port.plan_next_outcome(command.key, "unknown_before")

    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.ensure_business_party(command)
    assert port.created_count == 0
    assert port.inspect_synthetic_remote(command.key) is None

    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.ensure_business_party(command)
    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.confirm_observed_reference(command, "FAKE-PARTY-999999")
    assert port.created_count == 0


def test_unknown_after_write_is_not_replayed_until_positive_reconciliation():
    port = FakeBusinessPartyPort()
    command = make_request()
    port.plan_next_outcome(command.key, "unknown_after")

    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.ensure_business_party(command)
    observed = port.inspect_synthetic_remote(command.key)
    assert observed is not None
    assert port.created_count == 1

    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.ensure_business_party(command)
    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.confirm_observed_reference(command, "WRONG-ID")
    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.ensure_business_party(command)

    linked = port.confirm_observed_reference(command, observed.remote_id)
    assert linked == observed
    assert port.ensure_business_party(command) == observed
    assert port.created_count == 1


def test_unknown_reconciliation_cannot_switch_payload():
    port = FakeBusinessPartyPort()
    command = make_request()
    port.plan_next_outcome(command.key, "unknown_after")
    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.ensure_business_party(command)
    observed = port.inspect_synthetic_remote(command.key)
    assert observed is not None

    with pytest.raises(BusinessPartyConflict):
        port.confirm_observed_reference(
            make_request(display_name="Alterado depois"), observed.remote_id
        )
    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.ensure_business_party(command)
    assert port.created_count == 1


def test_unknown_one_tenant_does_not_block_other_tenant():
    port = FakeBusinessPartyPort()
    a = make_request()
    b = make_request(company_id=2)
    port.plan_next_outcome(a.key, "unknown_after")

    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.ensure_business_party(a)
    assert port.ensure_business_party(b).key == b.key
    assert port.created_count == 2


@pytest.mark.parametrize(
    "fields",
    [
        {"company_id": 0},
        {"company_id": True},
        {"customer_id": 0},
        {"customer_id": -1},
        {"connection_ref": ""},
        {"connection_ref": " erp "},
        {"connection_ref": "erp\nother"},
        {"connection_ref": "x" * 121},
    ],
)
def test_key_rejects_invalid_identity(fields):
    base = {"company_id": 1, "connection_ref": "erpnext-instance-a", "customer_id": 10}
    with pytest.raises(ValueError):
        BusinessPartyKey(**{**base, **fields})


@pytest.mark.parametrize(
    "display_name", ["", "   ", " Name", "Bad\nName", "x" * 121]
)
def test_payload_rejects_invalid_name(display_name):
    with pytest.raises(ValueError):
        make_request(display_name=display_name)


def test_fake_failure_programming_cannot_override_state():
    port = FakeBusinessPartyPort()
    command = make_request()
    port.plan_next_outcome(command.key, "unknown_before")
    with pytest.raises(ValueError):
        port.plan_next_outcome(command.key, "unknown_after")
    with pytest.raises(BusinessPartyOutcomeUnknown):
        port.ensure_business_party(command)
    with pytest.raises(ValueError):
        port.plan_next_outcome(command.key, "unavailable")

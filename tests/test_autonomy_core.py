"""Offline integration tests for the F2 durable commercial planner.

Only temporary SQLite is used; operational PostgreSQL and live n8n are untouched.
"""

from dataclasses import replace

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.database import Base
from app.models import Company
from app.services.autonomy_core import (
    AutonomyDecision,
    AutonomyJob,
    CampaignPolicy,
    Signal,
    finish_simulation,
    lease_due_simulation,
    prepare,
    retry_simulation,
)


NOW = 1_800_000_000


@pytest.fixture
def sandbox(tmp_path):
    engine = create_engine(f"sqlite+pysqlite:///{tmp_path / 'autonomy-test.sqlite'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([Company(id=1, name="Fictitious A", slug="demo-a"),
                    Company(id=2, name="Fictitious B", slug="demo-b")])
        db.commit()
    yield engine
    engine.dispose()


@pytest.fixture
def policy():
    return CampaignPolicy(
        company_id=1, version="authorized-synthetic-v1", expires_ts=NOW + 7200,
        enabled=True, channels=("email", "whatsapp")
    )


@pytest.fixture
def quote():
    return Signal(
        company_id=1, event_id="q-1", case_ref="quote-1",
        kind="quote", channel="email", consent_verified=True,
        opted_out=False, within_session_window=False,
        approved_template=False, days_since_quote=5
    )


def count(db, model):
    return db.scalar(select(func.count()).select_from(model))


def test_quote_prepares_job_without_sending(sandbox, policy, quote):
    with Session(sandbox) as db:
        row, created = prepare(
            db, trusted_company_id=1, policy=policy, signal=quote, now_ts=NOW
        )
        assert created and row.state == "prepared"
        assert row.reason == "eligible_draft"
        assert row.draft.startswith("Olá")
        assert count(db, AutonomyDecision) == 1
        assert count(db, AutonomyJob) == 1
        job = db.scalar(select(AutonomyJob))
        assert job.state == "pending"
        assert job.company_id == row.company_id
        assert job.decision_id == row.id


def test_inbound_qualification_draft(sandbox, policy, quote):
    lead = replace(quote, event_id="l-1", case_ref="lead-1",
                   kind="inbound_lead", days_since_quote=0)
    with Session(sandbox) as db:
        row, created = prepare(db, trusted_company_id=1, policy=policy,
                               signal=lead, now_ts=NOW)
        assert created and row.state == "prepared"
        assert "Qual serviço" in row.draft


def test_idempotency_survives_reopening_database(sandbox, policy, quote):
    with Session(sandbox) as db:
        first, created = prepare(db, trusted_company_id=1, policy=policy,
                                 signal=quote, now_ts=NOW)
        assert created
        first_id = first.id

    with Session(sandbox) as restarted:
        replay, created = prepare(
            restarted, trusted_company_id=1, policy=policy,
            signal=quote, now_ts=NOW + 60,
        )
        assert not created and replay.id == first_id
        assert count(restarted, AutonomyDecision) == 1
        assert count(restarted, AutonomyJob) == 1
        with pytest.raises(ValueError, match="Conflicting payload"):
            prepare(restarted, trusted_company_id=1, policy=policy,
                    signal=replace(quote, days_since_quote=99), now_ts=NOW + 60)


@pytest.mark.parametrize(
    ("modifications", "expected_state", "reason"),
    [
        ({"opted_out": True}, "blocked", "opt_out"),
        ({"consent_verified": False}, "blocked", "consent_not_verified"),
        ({"consent_verified": "yes"}, "blocked", "invalid_boolean_flags"),
        ({"opted_out": 0}, "blocked", "invalid_boolean_flags"),
        ({"channel": "whatsapp", "approved_template": "true"},
         "blocked", "invalid_boolean_flags"),
        ({"kind": "unexpected"}, "blocked", "unsupported_kind"),
        ({"channel": "sms"}, "blocked", "unauthorized_channel"),
        ({"days_since_quote": 1}, "deferred", "quote_followup_not_due"),
        ({"channel": "whatsapp"}, "blocked", "approved_template_required"),
        ({"channel": "whatsapp", "approved_template": True},
         "prepared", "eligible_draft"),
        ({"channel": "whatsapp", "within_session_window": True},
         "prepared", "eligible_draft"),
    ],
)
def test_policy_gate_fail_closed(
    sandbox, policy, quote, modifications, expected_state, reason
):
    with Session(sandbox) as db:
        signal = replace(quote, **modifications)
        row, _ = prepare(db, trusted_company_id=1, policy=policy,
                         signal=signal, now_ts=NOW)
        assert (row.state, row.reason) == (expected_state, reason)
        assert count(db, AutonomyJob) == int(expected_state == "prepared")


def test_disabled_and_expired_policies_create_no_work(sandbox, policy, quote):
    with Session(sandbox) as db:
        disabled, _ = prepare(
            db, trusted_company_id=1, policy=replace(policy, enabled=False),
            signal=quote, now_ts=NOW,
        )
        expired, _ = prepare(
            db, trusted_company_id=1, policy=replace(policy, expires_ts=NOW),
            signal=replace(quote, event_id="q-2"), now_ts=NOW,
        )
        assert disabled.state == expired.state == "blocked"
        assert count(db, AutonomyJob) == 0


def test_tenant_is_derived_from_trusted_identity_not_event(sandbox, policy, quote):
    with Session(sandbox) as db:
        with pytest.raises(ValueError, match="Company scope"):
            prepare(db, trusted_company_id=2, policy=policy,
                    signal=quote, now_ts=NOW)
        with pytest.raises(ValueError, match="Company scope"):
            prepare(db, trusted_company_id=1, policy=policy,
                    signal=replace(quote, company_id=2), now_ts=NOW)
        assert count(db, AutonomyDecision) == 0
        assert count(db, AutonomyJob) == 0


def test_weekly_case_limit_prevents_followups(sandbox, policy, quote):
    limited = replace(policy, max_drafts_per_case_week=1)
    with Session(sandbox) as db:
        first, _ = prepare(db, trusted_company_id=1, policy=limited,
                           signal=quote, now_ts=NOW)
        second, _ = prepare(db, trusted_company_id=1, policy=limited,
                            signal=replace(quote, event_id="q-2"), now_ts=NOW + 1)
        assert first.state == "prepared"
        assert (second.state, second.reason) == ("blocked", "weekly_case_limit")
        assert count(db, AutonomyJob) == 1


def test_unavailable_or_invalid_model_never_creates_job(sandbox, policy, quote):
    def failed(_):
        raise RuntimeError("Sensitive provider details must not be exposed")

    with Session(sandbox) as db:
        first, _ = prepare(db, trusted_company_id=1, policy=policy,
                           signal=quote, now_ts=NOW, composer=failed)
        second, _ = prepare(db, trusted_company_id=1, policy=policy,
                            signal=replace(quote, event_id="q-2"),
                            now_ts=NOW, composer=lambda _kind: "")
        third, _ = prepare(db, trusted_company_id=1, policy=policy,
                           signal=replace(quote, event_id="q-3"),
                           now_ts=NOW, composer=lambda _kind: "x" * 501)
        assert first.reason == "model_unavailable"
        assert second.reason == third.reason == "invalid_model_draft"
        assert first.state == second.state == third.state == "escalate"
        assert first.draft is None
        assert count(db, AutonomyJob) == 0


def test_blocked_event_never_calls_model(sandbox, policy, quote):
    def forbidden(_):
        raise AssertionError("Model must not see a blocked signal")

    with Session(sandbox) as db:
        row, _ = prepare(db, trusted_company_id=1, policy=policy,
                         signal=replace(quote, consent_verified=False),
                         now_ts=NOW, composer=forbidden)
        assert row.state == "blocked"


def test_leases_survive_restart_and_expire(sandbox, policy, quote):
    with Session(sandbox) as db:
        prepare(db, trusted_company_id=1, policy=policy,
                signal=quote, now_ts=NOW)
        job = lease_due_simulation(db, trusted_company_id=1,
                                   now_ts=NOW, lease_seconds=10)
        assert job and job.state == "leased"
        job_id, first_token = job.id, job.lease_token
        assert lease_due_simulation(db, trusted_company_id=1,
                                    now_ts=NOW + 5) is None

    with Session(sandbox) as db:
        again = lease_due_simulation(db, trusted_company_id=1,
                                     now_ts=NOW + 10, lease_seconds=10)
        assert again and again.id == job_id and again.attempts == 2
        assert again.lease_token != first_token
        assert not finish_simulation(db, trusted_company_id=1,
                                     job_id=job_id, token=first_token,
                                     now_ts=NOW + 11)
        assert not finish_simulation(db, trusted_company_id=2,
                                     job_id=job_id, token=again.lease_token,
                                     now_ts=NOW + 11)
        assert finish_simulation(db, trusted_company_id=1,
                                 job_id=job_id, token=again.lease_token,
                                 now_ts=NOW + 11)
        assert lease_due_simulation(db, trusted_company_id=1,
                                    now_ts=NOW + 50) is None
        assert db.get(AutonomyJob, job_id).state == "simulated"


def test_retry_backoff_and_dead_letter(sandbox, policy, quote):
    with Session(sandbox) as db:
        prepare(db, trusted_company_id=1, policy=policy,
                signal=quote, now_ts=NOW)
        first = lease_due_simulation(db, trusted_company_id=1, now_ts=NOW)
        assert retry_simulation(db, trusted_company_id=1, job_id=first.id,
                                token=first.lease_token, now_ts=NOW)
        assert db.get(AutonomyJob, first.id).due_ts == NOW + 60
        assert lease_due_simulation(db, trusted_company_id=1,
                                    now_ts=NOW + 59) is None
        second = lease_due_simulation(db, trusted_company_id=1, now_ts=NOW + 60)
        assert second.attempts == 2
        assert retry_simulation(db, trusted_company_id=1, job_id=second.id,
                                token=second.lease_token, now_ts=NOW + 60)
        assert db.get(AutonomyJob, first.id).due_ts == NOW + 180
        third = lease_due_simulation(db, trusted_company_id=1, now_ts=NOW + 180)
        assert third.attempts == 3
        assert retry_simulation(db, trusted_company_id=1, job_id=third.id,
                                token=third.lease_token, now_ts=NOW + 180)
        assert lease_due_simulation(db, trusted_company_id=1,
                                    now_ts=NOW + 420) is None
        assert db.get(AutonomyJob, first.id).state == "failed"


def test_cannot_claim_jobs_from_other_company(sandbox, policy, quote):
    with Session(sandbox) as db:
        prepare(db, trusted_company_id=1, policy=policy,
                signal=quote, now_ts=NOW)
        assert lease_due_simulation(db, trusted_company_id=2,
                                    now_ts=NOW) is None
        assert lease_due_simulation(db, trusted_company_id=1,
                                    now_ts=NOW) is not None

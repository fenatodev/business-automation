"""WP-559 — Direct coverage for the scheduled follow-up handler."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from app.models import Company, InternalTask, Opportunity
from app.services.followup import FollowupConfig, _followup_configs, set_followup_config
from app.services.scheduler import handle_followup_job
from conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def reset_followup_configs():
    _followup_configs.clear()
    yield
    _followup_configs.clear()


def _create_company(db, name: str) -> Company:
    company = Company(name=name, slug=name.lower())
    db.add(company)
    db.flush()
    return company


def _create_opportunity(
    db,
    company_id: int,
    *,
    name: str,
    age_days: int,
    outcome: str | None = None,
) -> Opportunity:
    opportunity = Opportunity(
        company_id=company_id,
        source="manual",
        external_url=f"https://example.test/{name}",
        title=name,
        description="Synthetic scheduled follow-up test",
        captured_at=datetime.now(timezone.utc) - timedelta(days=age_days),
        outcome=outcome,
    )
    db.add(opportunity)
    return opportunity


def test_handler_creates_tasks_only_for_enabled_tenant_stale_open_opportunities():
    with TestingSessionLocal() as db:
        active_company = _create_company(db, "wp559-active")
        unconfigured_company = _create_company(db, "wp559-unconfigured")
        stale = _create_opportunity(
            db, active_company.id, name="stale-open", age_days=30
        )
        _create_opportunity(
            db, active_company.id, name="recent-open", age_days=1
        )
        _create_opportunity(
            db, active_company.id, name="stale-closed", age_days=30, outcome="lost"
        )
        _create_opportunity(
            db, unconfigured_company.id, name="unconfigured-stale", age_days=30
        )
        db.commit()

        set_followup_config(FollowupConfig(active_company.id, stale_days=7))

        assert handle_followup_job({}, db=db) == 1

        tasks = db.scalars(select(InternalTask)).all()
        assert len(tasks) == 1
        assert tasks[0].company_id == active_company.id
        assert tasks[0].payload["opportunity_id"] == stale.id
        assert tasks[0].payload["title"] == "stale-open"
        assert tasks[0].status == "queued"


def test_handler_deduplicates_repeated_scheduler_runs_for_same_stale_opportunity():
    with TestingSessionLocal() as db:
        company = _create_company(db, "wp559-dedup")
        _create_opportunity(db, company.id, name="repeat-stale", age_days=30)
        db.commit()
        set_followup_config(FollowupConfig(company.id, stale_days=7))

        assert handle_followup_job({}, db=db) == 1
        assert handle_followup_job({}, db=db) == 0
        assert db.query(InternalTask).count() == 1


def test_handler_skips_company_with_disabled_followup_config():
    with TestingSessionLocal() as db:
        company = _create_company(db, "wp559-disabled")
        _create_opportunity(db, company.id, name="disabled-stale", age_days=30)
        db.commit()
        set_followup_config(
            FollowupConfig(company.id, stale_days=7, enabled=False)
        )

        assert handle_followup_job({}, db=db) == 0
        assert db.query(InternalTask).count() == 0


def test_handler_closes_session_it_creates_when_no_session_is_supplied(monkeypatch):
    with TestingSessionLocal() as db:
        company = _create_company(db, "wp559-owned-session")
        _create_opportunity(db, company.id, name="owned-stale", age_days=30)
        db.commit()
        company_id = company.id

    set_followup_config(FollowupConfig(company_id, stale_days=7))
    owned_session = TestingSessionLocal()
    close_spy = Mock(wraps=owned_session.close)
    monkeypatch.setattr(owned_session, "close", close_spy)
    monkeypatch.setattr("app.database.SessionLocal", lambda: owned_session)

    assert handle_followup_job({}) == 1
    close_spy.assert_called_once_with()

    with TestingSessionLocal() as db:
        assert db.query(InternalTask).count() == 1
"""Fail-closed F2 commercial action planner and durable *simulation* queue.

Models are deliberately not imported into app.main and have no migration yet.
Do not create these tables in the operational PostgreSQL without a reviewed WP.
The worker has NO external-dispatch method and can only acknowledge simulations.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import secrets
from typing import Callable

from sqlalchemy import ForeignKey, Integer, String, Text, UniqueConstraint, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.database import Base


class AutonomyDecision(Base):
    __tablename__ = "autonomy_decisions"
    __table_args__ = (
        UniqueConstraint("company_id", "event_id", name="uq_autonomy_company_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(120), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    case_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    kind: Mapped[str] = mapped_column(String(24), nullable=False)
    policy_version: Mapped[str] = mapped_column(String(50), nullable=False)
    state: Mapped[str] = mapped_column(String(24), nullable=False)
    reason: Mapped[str] = mapped_column(String(45), nullable=False)
    draft: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_ts: Mapped[int] = mapped_column(Integer, nullable=False)


class AutonomyJob(Base):
    __tablename__ = "autonomy_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id"), nullable=False, index=True)
    decision_id: Mapped[int] = mapped_column(
        ForeignKey("autonomy_decisions.id"), nullable=False, unique=True
    )
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    due_ts: Mapped[int] = mapped_column(Integer, nullable=False)
    lease_until_ts: Mapped[int | None] = mapped_column(Integer)
    lease_token: Mapped[str | None] = mapped_column(String(64))
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


@dataclass(frozen=True)
class CampaignPolicy:
    """Supplied only by an authenticated, versioned policy store (NOT by input events)."""

    company_id: int
    version: str
    expires_ts: int
    enabled: bool = False
    channels: tuple[str, ...] = ("email",)
    min_quote_age_days: int = 3
    max_drafts_per_case_week: int = 2


@dataclass(frozen=True)
class Signal:
    """Synthetic fixture or future validated connector signal. Contains no personal data."""

    company_id: int
    event_id: str
    case_ref: str
    kind: str
    channel: str
    consent_verified: bool
    opted_out: bool
    within_session_window: bool
    approved_template: bool
    days_since_quote: int = 0


def _validate(trusted_company_id: int, policy: CampaignPolicy, signal: Signal, now_ts: int):
    if type(trusted_company_id) is not int or trusted_company_id <= 0:
        raise ValueError("Trusted company ID required")
    if policy.company_id != trusted_company_id or signal.company_id != trusted_company_id:
        raise ValueError("Company scope mismatch")
    if type(now_ts) is not int or now_ts < 0:
        raise ValueError("Invalid clock")
    if (
        not policy.version
        or len(policy.version) > 50
        or type(policy.expires_ts) is not int
        or policy.min_quote_age_days < 0
        or policy.max_drafts_per_case_week < 1
        or len(policy.channels) == 0
    ):
        raise ValueError("Invalid trusted policy")
    if (
        not signal.event_id
        or len(signal.event_id) > 120
        or not signal.case_ref
        or len(signal.case_ref) > 120
    ):
        raise ValueError("Invalid event identity")


def _fingerprint(signal: Signal) -> str:
    canonical = json.dumps(
        asdict(signal), sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _decision(
    db: Session,
    policy: CampaignPolicy,
    signal: Signal,
    now_ts: int,
) -> tuple[str, str]:
    if not policy.enabled or now_ts >= policy.expires_ts:
        return "blocked", "policy_inactive_or_expired"
    if signal.kind not in ("quote", "inbound_lead"):
        return "blocked", "unsupported_kind"
    if signal.channel not in policy.channels:
        return "blocked", "unauthorized_channel"
    if signal.opted_out:
        return "blocked", "opt_out"
    if not signal.consent_verified:
        return "blocked", "consent_not_verified"
    if signal.channel == "whatsapp" and not (
        signal.within_session_window or signal.approved_template
    ):
        return "blocked", "approved_template_required"
    if signal.kind == "quote" and (
        type(signal.days_since_quote) is not int
        or signal.days_since_quote < policy.min_quote_age_days
    ):
        return "deferred", "quote_followup_not_due"
    since = now_ts - 7 * 86400
    count = db.scalar(
        select(func.count()).select_from(AutonomyDecision).where(
            AutonomyDecision.company_id == policy.company_id,
            AutonomyDecision.case_ref == signal.case_ref,
            AutonomyDecision.state == "prepared",
            AutonomyDecision.created_ts >= since,
        )
    )
    if count >= policy.max_drafts_per_case_week:
        return "blocked", "weekly_case_limit"
    return "prepared", "eligible_draft"


def prepare(
    db: Session,
    *,
    trusted_company_id: int,
    policy: CampaignPolicy,
    signal: Signal,
    now_ts: int,
    composer: Callable[[str], str] | None = None,
) -> tuple[AutonomyDecision, bool]:
    """Idempotently prepare an internal draft; never send or authorize a message.

    Returns (decision, created). A replay with a changed payload is rejected.
    Callers must pass trusted_company_id derived from authentication, not user JSON.
    """
    _validate(trusted_company_id, policy, signal, now_ts)
    digest = _fingerprint(signal)
    key = (
        AutonomyDecision.company_id == trusted_company_id,
        AutonomyDecision.event_id == signal.event_id,
    )
    existing = db.scalar(select(AutonomyDecision).where(*key))
    if existing is not None:
        if existing.fingerprint != digest:
            raise ValueError("Conflicting payload for existing event")
        return existing, False

    state, reason = _decision(db, policy, signal, now_ts)
    draft = None
    if state == "prepared":
        if composer is None:
            draft = (
                "Olá! Gostaria de saber se há dúvidas sobre seu orçamento. Podemos ajudar?"
                if signal.kind == "quote"
                else "Olá! Qual serviço você procura e em qual região?"
            )
        else:
            try:
                draft = composer(signal.kind)  # No raw external content in prompt.
            except Exception:
                state, reason = "escalate", "model_unavailable"
        if state == "prepared" and (
            not isinstance(draft, str)
            or not draft.strip()
            or len(draft) > 500
            or any(ord(char) < 32 and char not in "\n\t" for char in draft)
        ):
            draft = None
            state, reason = "escalate", "invalid_model_draft"

    decision = AutonomyDecision(
        company_id=trusted_company_id,
        event_id=signal.event_id,
        fingerprint=digest,
        case_ref=signal.case_ref,
        kind=signal.kind,
        policy_version=policy.version,
        state=state,
        reason=reason,
        draft=draft if state == "prepared" else None,
        created_ts=now_ts,
    )
    try:
        db.add(decision)
        db.flush()
        if state == "prepared":
            db.add(
                AutonomyJob(
                    company_id=trusted_company_id,
                    decision_id=decision.id,
                    state="pending",
                    due_ts=now_ts,
                    attempts=0,
                )
            )
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(AutonomyDecision).where(*key))
        if existing is None:
            raise
        if existing.fingerprint != digest:
            raise ValueError("Conflicting payload for existing event")
        return existing, False
    return decision, True


def lease_due_simulation(
    db: Session,
    *,
    trusted_company_id: int,
    now_ts: int,
    lease_seconds: int = 60,
    max_attempts: int = 3,
) -> AutonomyJob | None:
    """Lease a due *sandbox-only* job. PostgreSQL uses SKIP LOCKED.

    SQLite tests validate restart/retry semantics, NOT multi-worker concurrency.
    """
    if trusted_company_id <= 0 or now_ts < 0 or lease_seconds <= 0 or max_attempts <= 0:
        raise ValueError("Invalid lease parameters")
    candidates = db.scalars(
        select(AutonomyJob)
        .where(
            AutonomyJob.company_id == trusted_company_id,
            AutonomyJob.due_ts <= now_ts,
            or_(
                AutonomyJob.state == "pending",
                (AutonomyJob.state == "leased") & (AutonomyJob.lease_until_ts <= now_ts),
            ),
        )
        .order_by(AutonomyJob.due_ts, AutonomyJob.id)
        .with_for_update(skip_locked=True)
    ).all()
    for job in candidates:
        if job.attempts >= max_attempts:
            job.state = "failed"
            job.lease_token = None
            job.lease_until_ts = None
            db.commit()
            continue
        job.state = "leased"
        job.lease_token = secrets.token_hex(16)
        job.lease_until_ts = now_ts + lease_seconds
        job.attempts += 1
        db.commit()
        return job
    return None


def finish_simulation(
    db: Session, *, trusted_company_id: int, job_id: int, token: str, now_ts: int
) -> bool:
    """Record simulated completion only. No adapter capable of sending exists."""
    job = db.scalar(
        select(AutonomyJob).where(
            AutonomyJob.id == job_id, AutonomyJob.company_id == trusted_company_id
        )
    )
    if (
        job is None
        or job.state != "leased"
        or not token
        or not secrets.compare_digest(job.lease_token or "", token)
        or job.lease_until_ts is None
        or now_ts > job.lease_until_ts
    ):
        return False
    job.state = "simulated"
    job.lease_token = None
    job.lease_until_ts = None
    db.commit()
    return True


def retry_simulation(
    db: Session, *, trusted_company_id: int, job_id: int, token: str, now_ts: int
) -> bool:
    """Sandbox retry with exponential delay, no external effects."""
    job = db.scalar(
        select(AutonomyJob).where(
            AutonomyJob.id == job_id, AutonomyJob.company_id == trusted_company_id
        )
    )
    if (
        job is None
        or job.state != "leased"
        or not token
        or not secrets.compare_digest(job.lease_token or "", token)
        or job.lease_until_ts is None
        or now_ts > job.lease_until_ts
    ):
        return False
    job.state = "pending"
    job.lease_token = None
    job.lease_until_ts = None
    job.due_ts = now_ts + min(3600, 60 * (2 ** min(10, job.attempts - 1)))
    db.commit()
    return True

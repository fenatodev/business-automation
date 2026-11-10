"""Follow-up service for stale opportunities (WP-545).

Detects opportunities that have been inactive for a configurable period
and creates follow-up tasks automatically.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.models import Opportunity
from sqlalchemy import select
from sqlalchemy.orm import Session


class FollowupConfig:
    """Configuration for follow-up reminders."""

    def __init__(
        self,
        company_id: int,
        stale_days: int = 14,
        enabled: bool = True,
    ):
        self.company_id = company_id
        self.stale_days = stale_days
        self.enabled = enabled


class StaleOpportunity:
    """An opportunity that needs follow-up."""

    def __init__(
        self,
        opportunity_id: int,
        title: str,
        days_since_activity: int,
        next_action: str | None = None,
    ):
        self.opportunity_id = opportunity_id
        self.title = title
        self.days_since_activity = days_since_activity
        self.next_action = next_action


# In-memory store for follow-up configs
_followup_configs: dict[int, FollowupConfig] = {}


def set_followup_config(config: FollowupConfig) -> FollowupConfig:
    """Set follow-up config for a company."""
    _followup_configs[config.company_id] = config
    return config


def get_followup_config(company_id: int) -> FollowupConfig | None:
    """Get follow-up config for a company."""
    return _followup_configs.get(company_id)


def find_stale_opportunities(
    db: Session,
    company_id: int,
    stale_days: int | None = None,
) -> list[StaleOpportunity]:
    """Find opportunities that have been inactive for the configured period."""
    config = get_followup_config(company_id)
    if config and not config.enabled:
        return []

    if stale_days is None:
        if config:
            stale_days = config.stale_days
        else:
            stale_days = 14

    threshold = datetime.now(timezone.utc) - timedelta(days=stale_days)

    opportunities = db.scalars(
        select(Opportunity).where(
            Opportunity.company_id == company_id,
            Opportunity.outcome.is_(None),
        )
    ).all()

    stale: list[StaleOpportunity] = []
    for opp in opportunities:
        last_activity = opp.captured_at
        if last_activity.tzinfo is None:
            last_activity = last_activity.replace(tzinfo=timezone.utc)

        if last_activity < threshold:
            days_since = int(
                (datetime.now(timezone.utc) - last_activity).total_seconds() / 86400
            )
            stale.append(
                StaleOpportunity(
                    opportunity_id=opp.id,
                    title=opp.title or f"Opportunity #{opp.id}",
                    days_since_activity=days_since,
                    next_action=opp.next_action,
                )
            )

    return stale

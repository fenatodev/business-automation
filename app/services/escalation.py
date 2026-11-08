"""Escalation service for conversations (WP-544).

Detects conversations that exceed configurable response time thresholds
and flags them for escalation.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.models import Conversation, Message
from sqlalchemy import select
from sqlalchemy.orm import Session


class EscalationRule:
    """A rule that defines when a conversation should be escalated."""

    def __init__(
        self,
        name: str,
        company_id: int,
        max_response_minutes: int = 30,
        enabled: bool = True,
    ):
        self.name = name
        self.company_id = company_id
        self.max_response_minutes = max_response_minutes
        self.enabled = enabled


class EscalationAlert:
    """An alert for a conversation that needs escalation."""

    def __init__(
        self,
        conversation_id: int,
        conversation_title: str,
        last_customer_message_at: datetime,
        minutes_since_response: int,
        rule_name: str,
    ):
        self.conversation_id = conversation_id
        self.conversation_title = conversation_title
        self.last_customer_message_at = last_customer_message_at
        self.minutes_since_response = minutes_since_response
        self.rule_name = rule_name


# In-memory store for escalation rules
_escalation_rules: dict[int, list[EscalationRule]] = {}


def add_escalation_rule(rule: EscalationRule) -> EscalationRule:
    """Add an escalation rule for a company."""
    if rule.company_id not in _escalation_rules:
        _escalation_rules[rule.company_id] = []
    # Remove existing rule with same name
    _escalation_rules[rule.company_id] = [
        r for r in _escalation_rules[rule.company_id] if r.name != rule.name
    ]
    _escalation_rules[rule.company_id].append(rule)
    return rule


def get_escalation_rules(company_id: int) -> list[EscalationRule]:
    """Get all escalation rules for a company."""
    return _escalation_rules.get(company_id, [])


def remove_escalation_rule(company_id: int, rule_name: str) -> bool:
    """Remove an escalation rule by name."""
    rules = _escalation_rules.get(company_id, [])
    new_rules = [r for r in rules if r.name != rule_name]
    if len(new_rules) < len(rules):
        _escalation_rules[company_id] = new_rules
        return True
    return False


def check_escalations(db: Session, company_id: int) -> list[EscalationAlert]:
    """Check for conversations that need escalation based on rules."""
    rules = [r for r in get_escalation_rules(company_id) if r.enabled]
    if not rules:
        return []

    alerts: list[EscalationAlert] = []
    now = datetime.now(timezone.utc)

    for rule in rules:
        threshold = now - timedelta(minutes=rule.max_response_minutes)

        # Find conversations with recent customer messages but no agent response
        conversations = db.scalars(
            select(Conversation).where(
                Conversation.company_id == company_id,
                Conversation.status != "closed",
            )
        ).all()

        for conv in conversations:
            # Get last customer message
            last_customer_msg = db.scalars(
                select(Message)
                .where(
                    Message.conversation_id == conv.id,
                    Message.sender_type == "customer",
                )
                .order_by(Message.id.desc())
            ).first()

            if not last_customer_msg:
                continue

            # Check if there's an agent response after the last customer message
            agent_response = db.scalars(
                select(Message)
                .where(
                    Message.conversation_id == conv.id,
                    Message.sender_type == "agent",
                    Message.id > last_customer_msg.id,
                )
                .order_by(Message.id)
            ).first()

            if agent_response:
                continue

            # Check if the customer message is older than the threshold
            msg_time = last_customer_msg.created_at
            if msg_time.tzinfo is None:
                msg_time = msg_time.replace(tzinfo=timezone.utc)

            if msg_time < threshold:
                minutes_since = int(
                    (now - msg_time).total_seconds() / 60
                )
                alerts.append(
                    EscalationAlert(
                        conversation_id=conv.id,
                        conversation_title=conv.title or f"Conversation #{conv.id}",
                        last_customer_message_at=msg_time,
                        minutes_since_response=minutes_since,
                        rule_name=rule.name,
                    )
                )

    return alerts

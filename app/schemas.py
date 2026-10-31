from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LeadCreate(BaseModel):
    company_id: int
    name: str
    phone: str
    source: str
    interest: str | None = None


class AgentRequest(BaseModel):
    content: str
    system_prompt: str | None = None  # WP-202 — optional custom system prompt


class ConversationCreate(BaseModel):
    company_id: int
    channel: Literal[
        "whatsapp",
        "instagram",
        "web",
        "telegram",
        "email",
    ]
    lead_id: int | None = None
    customer_id: int | None = None


class ConversationUpdate(BaseModel):
    """Update conversation status and/or internal note."""
    status: Literal["open", "closed"] | None = None
    note: str | None = Field(default=None, max_length=2000)


class ConversationBulkStatus(BaseModel):
    """Bulk update status for multiple conversations."""
    conversation_ids: list[int] = Field(min_length=1, max_length=100)
    status: Literal["open", "closed"]


class MessageCreate(BaseModel):
    sender_type: Literal[
        "customer",
        "agent",
        "human",
        "system",
    ]
    content: str        


class CustomerCreate(BaseModel):
    company_id: int
    name: str
    phone: str
    email: str | None = None


class CustomerUpdate(BaseModel):
    """Update customer name, phone, and/or email."""
    name: str | None = Field(default=None, min_length=1, max_length=120)
    phone: str | None = Field(default=None, max_length=30)
    email: str | None = Field(default=None, max_length=120)


class CustomerBulkDelete(BaseModel):
    """Bulk delete multiple customers."""
    customer_ids: list[int] = Field(min_length=1, max_length=100)


class LeadUpdate(BaseModel):
    status: Literal[
        "new",
        "contacted",
        "qualified",
        "proposal",
        "won",
        "lost",
    ] | None = None
    interest: str | None = None


class LeadBulkStatus(BaseModel):
    """Bulk update status for multiple leads."""
    lead_ids: list[int] = Field(min_length=1, max_length=100)
    status: Literal[
        "new",
        "contacted",
        "qualified",
        "proposal",
        "won",
        "lost",
    ]


class LeadBulkDelete(BaseModel):
    """Bulk delete multiple leads."""
    lead_ids: list[int] = Field(min_length=1, max_length=100)


class CompanyCreate(BaseModel):
    name: str
    slug: str



class OpportunityCreate(BaseModel):
    source: Literal["99freelas", "intake", "review_queue", "manual", "import"]
    external_url: str = Field(min_length=1, max_length=1000)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    budget: str | None = Field(default=None, max_length=120)
    deadline: str | None = Field(default=None, max_length=120)
    requirements: str | None = None
    captured_at: datetime


class IntakeCreate(BaseModel):
    """Request body for creating an opportunity from commercial intake."""

    model_config = ConfigDict(extra="forbid")

    channel: str = Field(min_length=1, max_length=30)
    message: str = Field(min_length=1, max_length=4000)
    event_id: str = Field(min_length=1, max_length=100)

    @field_validator("channel", "message", "event_id")
    @classmethod
    def nonempty_printable(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("intake field cannot be blank")
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("intake field contains control characters")
        return value


class IntakeCreateResponse(BaseModel):
    """Response after evaluating and persisting a commercial intake."""

    opportunity_id: int
    event_id: str
    intent: str
    needs_human_review: bool
    flags: list[str]


class OpportunityUpdate(BaseModel):
    """Update opportunity title, description and/or triage note."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    triage_note: str | None = None


class OpportunityTriageUpdate(BaseModel):
    next_action: Literal[
        "pending",
        "ignore",
        "follow",
        "prepare_proposal",
        "in_progress",
        "done",
        "lost",
    ]
    triage_note: str | None = None


class OpportunityBulkTriage(BaseModel):
    """Apply the same triage action to multiple opportunities at once."""

    model_config = ConfigDict(extra="forbid")

    opportunity_ids: list[int] = Field(min_length=1, max_length=100)
    next_action: Literal[
        "pending",
        "ignore",
        "follow",
        "prepare_proposal",
        "in_progress",
        "done",
        "lost",
    ]
    triage_note: str | None = Field(default=None, max_length=2000)


class OpportunityBulkDelete(BaseModel):
    """Bulk delete multiple opportunities."""

    model_config = ConfigDict(extra="forbid")

    opportunity_ids: list[int] = Field(min_length=1, max_length=100)


class ConversationBulkDelete(BaseModel):
    """Bulk delete multiple conversations."""

    model_config = ConfigDict(extra="forbid")

    conversation_ids: list[int] = Field(min_length=1, max_length=100)


class ProposalBriefCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offer_reference: str = Field(min_length=1, max_length=120)
    diagnosis: str = Field(min_length=1)
    scope: str = Field(min_length=1)
    deliverables: str = Field(min_length=1)
    acceptance_criteria: str = Field(min_length=1)
    assumptions: str | None = None
    risks: str | None = None


class ProposalBriefUpdate(BaseModel):
    """Partial update for proposal brief — all fields optional."""

    model_config = ConfigDict(extra="forbid")

    offer_reference: str | None = Field(default=None, min_length=1, max_length=120)
    diagnosis: str | None = Field(default=None, min_length=1)
    scope: str | None = Field(default=None, min_length=1)
    deliverables: str | None = Field(default=None, min_length=1)
    acceptance_criteria: str | None = Field(default=None, min_length=1)
    assumptions: str | None = None
    risks: str | None = None
    status: Literal[
        "draft",
        "ready_for_review",
    ] | None = None


class ProposalBriefBulkStatus(BaseModel):
    """Bulk update status for multiple proposal briefs."""

    model_config = ConfigDict(extra="forbid")

    brief_ids: list[int] = Field(min_length=1, max_length=100)
    status: Literal[
        "draft",
        "ready_for_review",
    ]


class ProposalBriefBulkDelete(BaseModel):
    """Bulk delete multiple proposal briefs."""

    model_config = ConfigDict(extra="forbid")

    brief_ids: list[int] = Field(min_length=1, max_length=100)


class CommercialIntakeEvaluateRequest(BaseModel):
    """Request body for the private commercial intake evaluate endpoint.

    Only channel, message, and event_id are accepted.  All configuration
    (service_context, provider, model, flags, can_send) comes from the
    server side and must never be controlled by the caller.
    """

    model_config = ConfigDict(extra="forbid")

    channel: str = Field(min_length=1, max_length=30)
    message: str = Field(min_length=1, max_length=4000)
    event_id: str = Field(min_length=1, max_length=100)

    @field_validator("channel", "message", "event_id")
    @classmethod
    def nonempty_printable(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("commercial intake field cannot be blank")
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("commercial intake field contains control characters")
        return value


# ---------------------------------------------------------------------------
# Review Queue — WP-058
# ---------------------------------------------------------------------------


class ReviewQueueTrigger(BaseModel):
    """Request body for triggering a synthetic review queue item."""

    model_config = ConfigDict(extra="forbid")

    channel: str = Field(min_length=1, max_length=30)
    message: str = Field(min_length=1, max_length=4000)
    event_id: str = Field(min_length=1, max_length=100)

    @field_validator("channel", "message", "event_id")
    @classmethod
    def nonempty_printable(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("review queue field cannot be blank")
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("review queue field contains control characters")
        return value


class ReviewQueueDecision(BaseModel):
    """Operator decision for a review queue item."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    operator_note: str | None = Field(default=None, max_length=2000)


class ReviewQueueItemOut(BaseModel):
    """Output schema for review queue items."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    event_id: str
    channel: str
    message: str
    intent: str | None = None
    draft_reply: str | None = None
    status: str
    operator_note: str | None = None
    needs_human_review: bool
    flags_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class ReviewQueueBulkDecision(BaseModel):
    """Bulk decision for multiple review queue items."""

    model_config = ConfigDict(extra="forbid")

    item_ids: list[int] = Field(min_length=1, max_length=100)
    decision: Literal["approve", "reject"]
    operator_note: str | None = Field(default=None, max_length=2000)


class ReviewQueueDecisionResponse(BaseModel):
    """Response for review queue decision, includes opportunity_id when created."""

    id: int
    company_id: int
    event_id: str
    channel: str
    message: str
    intent: str | None = None
    draft_reply: str | None = None
    status: str
    operator_note: str | None = None
    needs_human_review: bool
    flags_json: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime
    opportunity_id: int | None = None


class InternalTaskBulkRetry(BaseModel):
    """Bulk retry multiple failed internal tasks."""

    model_config = ConfigDict(extra="forbid")

    task_ids: list[int] = Field(min_length=1, max_length=100)


class InternalTaskOut(BaseModel):
    """Operational status only: no message, payload, worker token or raw error."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    event_id: str
    status: Literal["queued", "running", "succeeded", "failed"]
    attempts: int
    result: dict[str, int] | None = None
    error_code: str | None = None
    created_at: datetime

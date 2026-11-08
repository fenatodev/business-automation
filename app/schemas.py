from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LeadCreate(BaseModel):
    company_id: int
    name: str
    phone: str
    source: str
    interest: str | None = None


class AgentRequest(BaseModel):
    content: str
    system_prompt: str | None = None  # WP-202 — optional custom system prompt
    temperature: float | None = None  # WP-203 — optional temperature (0.0-2.0)
    max_tokens: int | None = None  # WP-208 — optional max tokens
    model: str | None = None  # WP-213 — optional model override

    @field_validator("temperature")
    @classmethod
    def temperature_range(cls, v: float | None) -> float | None:
        if v is not None and (v < 0.0 or v > 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v

    @field_validator("max_tokens")
    @classmethod
    def max_tokens_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("max_tokens must be at least 1")
        return v

    @field_validator("model")
    @classmethod
    def model_not_empty(cls, v: str | None) -> str | None:
        """WP-219 — Reject empty or overly long model names."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("model cannot be empty")
            if len(v) > 100:
                raise ValueError("model name is too long (max 100 chars)")
        return v


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


class LeadSuggestion(BaseModel):
    """AI-generated lead suggestion from conversation context."""

    suggested_name: str | None = None
    suggested_phone: str | None = None
    suggested_interest: str | None = None
    reasoning: str


class CustomerSuggestion(BaseModel):
    """AI-generated customer suggestion from conversation context."""

    suggested_name: str | None = None
    suggested_phone: str | None = None
    suggested_email: str | None = None
    reasoning: str


class OpportunitySuggestion(BaseModel):
    """AI-generated opportunity suggestion from conversation context."""

    suggested_title: str | None = None
    suggested_description: str | None = None
    suggested_budget: str | None = None
    suggested_deadline: str | None = None
    suggested_requirements: str | None = None
    reasoning: str


class ConversationSummary(BaseModel):
    """AI-generated conversation summary."""

    summary: str
    key_points: list[str] | None = None
    action_items: list[str] | None = None


class LeadOpportunitySuggestion(BaseModel):
    """AI-generated opportunity suggestion from lead context."""

    suggested_title: str | None = None
    suggested_description: str | None = None
    suggested_budget: str | None = None
    suggested_deadline: str | None = None
    suggested_requirements: str | None = None
    reasoning: str


class CustomerOpportunitySuggestion(BaseModel):
    """AI-generated opportunity suggestion from customer context."""

    suggested_title: str | None = None
    suggested_description: str | None = None
    suggested_budget: str | None = None
    suggested_deadline: str | None = None
    suggested_requirements: str | None = None
    reasoning: str


class CustomerLeadSuggestion(BaseModel):
    """AI-generated lead suggestion from customer context."""

    suggested_name: str | None = None
    suggested_phone: str | None = None
    suggested_interest: str | None = None
    reasoning: str


class ConversationMessageSuggestion(BaseModel):
    """AI-generated first message suggestion for a new conversation."""

    suggested_message: str
    reasoning: str


class CompanyCreate(BaseModel):
    name: str
    slug: str


class CompanyAgentConfig(BaseModel):
    """Per-company agent configuration."""
    system_prompt: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None  # WP-208 — optional max tokens
    model: str | None = None  # WP-213 — optional model override (e.g., "qwen3:8b")

    @field_validator("temperature")
    @classmethod
    def temperature_range(cls, v: float | None) -> float | None:
        if v is not None and (v < 0.0 or v > 2.0):
            raise ValueError("temperature must be between 0.0 and 2.0")
        return v

    @field_validator("max_tokens")
    @classmethod
    def max_tokens_positive(cls, v: int | None) -> int | None:
        if v is not None and v < 1:
            raise ValueError("max_tokens must be at least 1")
        return v

    @field_validator("model")
    @classmethod
    def model_not_empty(cls, v: str | None) -> str | None:
        """WP-219 — Reject empty or overly long model names."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("model cannot be empty")
            if len(v) > 100:
                raise ValueError("model name is too long (max 100 chars)")
        return v


class OpportunityCreate(BaseModel):
    source: Literal["99freelas", "intake", "review_queue", "manual", "import"]
    external_url: str = Field(min_length=1, max_length=1000)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    budget: str | None = Field(default=None, max_length=120)
    deadline: str | None = Field(default=None, max_length=120)
    requirements: str | None = None
    captured_at: datetime
    lead_id: int | None = None
    customer_id: int | None = None

    @model_validator(mode="after")
    def one_contact(self):
        if self.lead_id is not None and self.customer_id is not None:
            raise ValueError("opportunity cannot belong to both lead and customer")
        return self


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


class IntakeSuggestion(BaseModel):
    """AI-generated intake suggestion for pre-validation."""

    suggested_intent: str
    suggested_category: str | None = None
    reasoning: str
    confidence: float | None = None


class OpportunityUpdate(BaseModel):
    """Update opportunity title, description and/or triage note."""
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, min_length=1)
    triage_note: str | None = None
    lead_id: int | None = None
    customer_id: int | None = None

    @model_validator(mode="after")
    def one_contact(self):
        if self.lead_id is not None and self.customer_id is not None:
            raise ValueError("opportunity cannot belong to both lead and customer")
        return self


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


class OpportunityTriageSuggestion(BaseModel):
    """Response from AI-assisted triage suggestion."""

    suggested_action: Literal[
        "pending",
        "ignore",
        "follow",
        "prepare_proposal",
        "in_progress",
        "done",
        "lost",
    ]
    reasoning: str
    confidence: float | None = None


class OpportunityBulkTriageSuggestion(BaseModel):
    """Request for AI-assisted bulk triage suggestion."""

    model_config = ConfigDict(extra="forbid")

    opportunity_ids: list[int] = Field(min_length=1, max_length=100)


class OpportunityBulkTriageSuggestionResponse(BaseModel):
    """Response from AI-assisted bulk triage suggestion."""

    suggested_action: Literal[
        "pending",
        "ignore",
        "follow",
        "prepare_proposal",
        "in_progress",
        "done",
        "lost",
    ]
    reasoning: str
    matching_count: int
    total_count: int


class OpportunityClose(BaseModel):
    """Close an opportunity as won or lost with optional reason and final value."""

    model_config = ConfigDict(extra="forbid")

    outcome: Literal["won", "lost"]
    reason: str | None = Field(default=None, max_length=2000)
    final_value: str | None = Field(default=None, max_length=120)


class ConversationBulkDelete(BaseModel):
    """Bulk delete multiple conversations."""

    model_config = ConfigDict(extra="forbid")

    conversation_ids: list[int] = Field(min_length=1, max_length=100)


class ReplyTemplateCreate(BaseModel):
    """Create a reusable reply template."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=100)
    content: str = Field(min_length=1, max_length=4000)


class ReplyTemplate(BaseModel):
    """Reply template for reuse in conversations."""

    id: int
    name: str
    content: str


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


class ProposalBriefSuggestion(BaseModel):
    """AI-generated proposal brief suggestion."""

    offer_reference: str
    diagnosis: str
    scope: str
    deliverables: str
    acceptance_criteria: str
    assumptions: str | None = None
    risks: str | None = None


class ProposalBriefDecision(BaseModel):
    """Operator decision for a proposal brief (approve or reject with optional note)."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["approve", "reject"]
    operator_note: str | None = Field(default=None, max_length=2000)


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


class ReviewQueueBulkDelete(BaseModel):
    """Bulk delete multiple review queue items."""

    model_config = ConfigDict(extra="forbid")

    item_ids: list[int] = Field(min_length=1, max_length=100)


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


# ---------------------------------------------------------------------------
# WP-520 — Global search
# ---------------------------------------------------------------------------


class GlobalSearchResult(BaseModel):
    """Single result from global search."""

    entity_type: str  # "opportunity", "conversation", "lead", "customer"
    entity_id: int
    title: str
    snippet: str | None = None


class GlobalSearchResponse(BaseModel):
    """Response for global search endpoint."""

    opportunities: list[GlobalSearchResult] = []
    conversations: list[GlobalSearchResult] = []
    leads: list[GlobalSearchResult] = []
    customers: list[GlobalSearchResult] = []


# ---------------------------------------------------------------------------
# WP-521 — Favorites
# ---------------------------------------------------------------------------


class FavoriteToggle(BaseModel):
    """Toggle favorite status for an entity."""

    model_config = ConfigDict(extra="forbid")

    favorited: bool


class FavoriteResponse(BaseModel):
    """Response for favorite toggle."""

    entity_type: str  # "opportunity" or "conversation"
    entity_id: int
    favorited: bool
    favorited_at: datetime | None = None


# ---------------------------------------------------------------------------
# WP-522 — Activity feed
# ---------------------------------------------------------------------------


class ActivityItem(BaseModel):
    """Single activity item in the feed."""

    activity_type: str  # "opportunity_created", "brief_approved", "brief_rejected", "conversation_replied", "lead_converted", "opportunity_closed"
    entity_id: int
    title: str
    timestamp: datetime


class ActivityFeedResponse(BaseModel):
    """Response for activity feed endpoint."""

    items: list[ActivityItem] = []

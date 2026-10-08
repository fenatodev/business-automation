from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field


class LeadCreate(BaseModel):
    company_id: int
    name: str
    phone: str
    source: str
    interest: str | None = None


class AgentRequest(BaseModel):
    content: str    


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


class LeadUpdate(BaseModel):
    status: Literal[
        "new",
        "contacted",
        "qualified",
        "proposal",
        "won",
        "lost",
    ]


class CompanyCreate(BaseModel):
    name: str
    slug: str



class OpportunityCreate(BaseModel):
    source: Literal["99freelas"]
    external_url: str = Field(min_length=1, max_length=1000)
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1)
    budget: str | None = Field(default=None, max_length=120)
    deadline: str | None = Field(default=None, max_length=120)
    requirements: str | None = None
    captured_at: AwareDatetime


class OpportunityTriageUpdate(BaseModel):
    next_action: Literal[
        "pending",
        "ignore",
        "follow",
        "prepare_proposal",
    ]
    triage_note: str | None = None

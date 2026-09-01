from typing import Literal

from pydantic import BaseModel


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

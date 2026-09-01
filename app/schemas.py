from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


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


class CompanyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class CompanyAgentConfigUpdate(BaseModel):
    instructions: str | None
    model: str | None

    @field_validator("instructions", "model")
    @classmethod
    def strip_non_empty_strings(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty")
        return value

    @field_validator("instructions")
    @classmethod
    def limit_instructions(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 10_000:
            raise ValueError("Instructions must not exceed 10000 characters")
        return value

    @field_validator("model")
    @classmethod
    def limit_model(cls, value: str | None) -> str | None:
        if value is not None and len(value) > 120:
            raise ValueError("Model must not exceed 120 characters")
        return value


class CompanyAgentConfigResponse(BaseModel):
    company_id: int
    instructions: str | None
    model: str | None
    effective_model: str

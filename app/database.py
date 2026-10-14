from typing import Literal

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str
    ollama_url: str = "http://localhost:11434"
    ollama_model: str = "qwen3:8b"
    access_identities_json: str = Field(
        default="[]",
        validation_alias="BA_ACCESS_IDENTITIES_JSON",
    )
    intake_generator: Literal["static", "ollama"] = Field(
        default="static",
        validation_alias="BA_INTAKE_GENERATOR",
    )
    intake_service_context: str = Field(
        default="Automação de processos e integrações sob diagnóstico.",
        min_length=1,
        max_length=2000,
        validation_alias="BA_INTAKE_SERVICE_CONTEXT",
    )

    @field_validator("intake_service_context")
    @classmethod
    def validate_intake_service_context(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("BA_INTAKE_SERVICE_CONTEXT cannot be blank")
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError("BA_INTAKE_SERVICE_CONTEXT contains control characters")
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()

engine = create_engine(settings.database_url)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


class Base(DeclarativeBase):
    pass

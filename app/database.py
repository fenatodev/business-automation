from typing import Literal

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from pydantic import Field
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
        validation_alias="BA_INTAKE_SERVICE_CONTEXT",
    )

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

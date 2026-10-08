"""Contrato mínimo para o primeiro handoff de contraparte comercial.

Este módulo NÃO realiza I/O, não concede autorização e não define DocTypes
do ERPNext. Uma camada autorizada deverá validar identidade, tenant, Customer
e aprovação humana ANTES de invocar uma implementação remota futura.
"""

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable


def _required_text(label: str, value: str, max_length: int) -> None:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > max_length
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise ValueError(f"{label} deve ser texto não vazio, sem controles, até {max_length} caracteres")


@dataclass(frozen=True, slots=True)
class BusinessPartyKey:
    """Identidade local + conexão autorizada; NUNCA usar apenas nome/email."""

    company_id: int
    connection_ref: str
    customer_id: int

    def __post_init__(self) -> None:
        for field, value in (
            ("company_id", self.company_id),
            ("customer_id", self.customer_id),
        ):
            if type(value) is not int or value < 1:
                raise ValueError(f"{field} deve ser inteiro positivo")
        _required_text("connection_ref", self.connection_ref, 120)


@dataclass(frozen=True, slots=True)
class BusinessPartyRequest:
    key: BusinessPartyKey
    display_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, BusinessPartyKey):
            raise ValueError("key deve ser BusinessPartyKey")
        _required_text("display_name", self.display_name, 120)


@dataclass(frozen=True, slots=True)
class BusinessPartyReference:
    """ID remoto estável; não significa proposta, cobrança nem cliente aprovado."""

    key: BusinessPartyKey
    remote_id: str

    def __post_init__(self) -> None:
        if not isinstance(self.key, BusinessPartyKey):
            raise ValueError("key deve ser BusinessPartyKey")
        _required_text("remote_id", self.remote_id, 200)


class BusinessPartyConflict(Exception):
    """Mesmo vínculo local recebeu dados incompatíveis; requer revisão."""


class BusinessPartyRejected(Exception):
    """Rejeição definitiva pelo destino; não repetir automaticamente."""

    def __init__(self, reason: Literal["validation", "permission"]) -> None:
        self.reason = reason
        super().__init__(reason)


class BusinessPartyUnavailable(Exception):
    """Indisponível antes de haver tentativa de escrita remota."""


class BusinessPartyOutcomeUnknown(Exception):
    """Pode ter gravado remotamente; reconciliação antes de qualquer retry."""


@runtime_checkable
class BusinessPartyPort(Protocol):
    def ensure_business_party(
        self, request: BusinessPartyRequest
    ) -> BusinessPartyReference:
        """Vínculo idempotente por (Company, conexão, Customer).

        Sem autorização implícita; sem promessa de exatamente-uma-vez no ERP.
        """
        ...

"""Simulador em memória do handoff de contraparte — sem rede ou banco.

Somente para testes. Não expor como endpoint ou serviço operacional.
"""

from typing import Literal

from app.services.business_party_port import (
    BusinessPartyConflict,
    BusinessPartyKey,
    BusinessPartyOutcomeUnknown,
    BusinessPartyReference,
    BusinessPartyRejected,
    BusinessPartyRequest,
    BusinessPartyUnavailable,
)

FakeOutcome = Literal[
    "reject_validation",
    "reject_permission",
    "unavailable",
    "unknown_before",
    "unknown_after",
]


class FakeBusinessPartyPort:
    """Simula idempotência local, rejeição e resultado remoto incerto.

    UNKNOWN fica bloqueado, mesmo depois de uma consulta sem resultado:
    ausência em uma consulta NÃO prova que a criação remota não ocorreu.
    """

    def __init__(self) -> None:
        self._parties: dict[
            BusinessPartyKey,
            tuple[BusinessPartyRequest, BusinessPartyReference],
        ] = {}
        self._planned: dict[BusinessPartyKey, FakeOutcome] = {}
        self._unknown: set[BusinessPartyKey] = set()
        self._last_number = 0

    @property
    def created_count(self) -> int:
        return len(self._parties)

    def plan_next_outcome(
        self, key: BusinessPartyKey, outcome: FakeOutcome
    ) -> None:
        if outcome not in (
            "reject_validation", "reject_permission", "unavailable",
            "unknown_before", "unknown_after",
        ):
            raise ValueError("Resultado simulado inválido")
        if key in self._parties or key in self._unknown or key in self._planned:
            raise ValueError("Não é possível programar outro resultado para este vínculo")
        self._planned[key] = outcome

    def _create(
        self, request: BusinessPartyRequest
    ) -> BusinessPartyReference:
        self._last_number += 1
        ref = BusinessPartyReference(
            key=request.key, remote_id=f"FAKE-PARTY-{self._last_number:06d}"
        )
        self._parties[request.key] = (request, ref)
        return ref

    def ensure_business_party(
        self, request: BusinessPartyRequest
    ) -> BusinessPartyReference:
        key = request.key
        if key in self._unknown:
            raise BusinessPartyOutcomeUnknown("Estado remoto desconhecido; não repetir")

        existing = self._parties.get(key)
        if existing is not None:
            old_request, ref = existing
            if old_request != request:
                raise BusinessPartyConflict("Vínculo local existe com dados diferentes")
            return ref

        outcome = self._planned.pop(key, None)
        if outcome == "reject_validation":
            raise BusinessPartyRejected("validation")
        if outcome == "reject_permission":
            raise BusinessPartyRejected("permission")
        if outcome == "unavailable":
            raise BusinessPartyUnavailable("Destino indisponível antes da escrita")
        if outcome == "unknown_before":
            self._unknown.add(key)
            raise BusinessPartyOutcomeUnknown("Timeout; gravação remota indeterminada")
        if outcome == "unknown_after":
            self._create(request)
            self._unknown.add(key)
            raise BusinessPartyOutcomeUnknown("Timeout após possível gravação")
        return self._create(request)

    def inspect_synthetic_remote(
        self, key: BusinessPartyKey
    ) -> BusinessPartyReference | None:
        """Retorna estado da memória fake; NÃO libera retry nem prova ausência real."""
        record = self._parties.get(key)
        return record[1] if record else None

    def confirm_observed_reference(
        self, request: BusinessPartyRequest, observed_remote_id: str
    ) -> BusinessPartyReference:
        """Somente teste de reconciliação POSITIVA no fake; não faz consulta real.

        Nunca aceita 'ausente' como prova suficiente para retry após timeout.
        """
        if request.key not in self._unknown:
            raise ValueError("Nenhum estado desconhecido a reconciliar")

        record = self._parties.get(request.key)
        if record is None or record[1].remote_id != observed_remote_id:
            raise BusinessPartyOutcomeUnknown("Nenhuma referência remota confirmada")
        if record[0] != request:
            raise BusinessPartyConflict("Dados divergentes; revisar antes de prosseguir")

        self._unknown.remove(request.key)
        return record[1]

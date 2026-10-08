"""Piloto Client 0 inteiramente sintetico e isolado (sem rede externa/ERP).

As classificacoes sao decisoes de cenario humano, nao regras automaticas.
tests/conftest.py injeta SQLite em memoria e credenciais exclusivamente de teste.
"""

import pytest


SCENARIOS = [
    pytest.param(
        {
            "name": "integracao-viavel",
            "title": "Integrar pedidos de loja ao CRM via API",
            "description": (
                "Loja ficticia exporta pedidos manualmente; deseja sincronizacao "
                "unidirecional via API com validacao e registro de falhas."
            ),
            "requirements": "API documentada, identificador unico e ambiente de homologacao.",
            "budget": None,
            "deadline": "A combinar",
            "next_action": "prepare_proposal",
            "triage_note": (
                "Problema delimitado; preparar diagnostico interno. "
                "Confirmar autenticacao e volume antes de prometer entrega."
            ),
        },
        id="preparar-proposta",
    ),
    pytest.param(
        {
            "name": "requisitos-incompletos",
            "title": "Organizar planilhas e integrar com sistema existente",
            "description": (
                "Empresa ficticia deseja automatizar lancamentos, mas ainda "
                "nao informou sistema de destino, permissao de API nem volume."
            ),
            "requirements": "Sistema, volume, acesso e criterios de aceite desconhecidos.",
            "budget": None,
            "deadline": None,
            "next_action": "follow",
            "triage_note": (
                "Solicitar detalhes do sistema e acesso antes de definir escopo; "
                "nao produzir brief prematuramente."
            ),
        },
        id="acompanhar",
    ),
    pytest.param(
        {
            "name": "escopo-inseguro",
            "title": "Extrair dados privados de terceiros sem autorizacao",
            "description": (
                "Solicitante ficticio pede acesso a dados pessoais de terceiros "
                "sem demonstrar autorizacao ou finalidade legitima."
            ),
            "requirements": "Coleta de dados de terceiros sem base demonstrada.",
            "budget": "Nao informado",
            "deadline": "Imediato",
            "next_action": "ignore",
            "triage_note": (
                "Rejeitar: risco de privacidade e ausencia de autorizacao. "
                "Nao elaborar proposta."
            ),
        },
        id="ignorar",
    ),
]


BRIEF = {
    "offer_reference": "client0-integracao-api-v1",
    "diagnosis": (
        "Processo manual de transferencia de pedidos; validar acesso a API, "
        "volume e regras de deduplicacao com o interessado."
    ),
    "scope": (
        "Prototipo de sincronizacao unidirecional em ambiente de homologacao; "
        "sem efeitos em producao ate aprovacao especifica."
    ),
    "deliverables": (
        "Conector demonstravel, testes de duplicidade/falha, "
        "documentacao de operacao e procedimento de reversao."
    ),
    "acceptance_criteria": (
        "Pedidos sinteticos chegam uma unica vez ao CRM ficticio; "
        "falhas ficam registradas e podem ser reprocessadas."
    ),
    "assumptions": "Cliente forneceria API documentada e homologacao.",
    "risks": "Limites da API, autenticacao e qualidade dos dados ainda desconhecidos.",
}


@pytest.mark.parametrize("scenario", SCENARIOS)
def test_client0_piloto_sintetico(
    client,
    admin_headers,
    operator_a_headers,
    scenario,
):
    # Nenhum dado real e criado: o banco e SQLite em memoria (conftest.py).
    company_response = client.post(
        "/companies",
        headers=admin_headers,
        json={"name": "Client 0 Sintetico", "slug": "client0-sintetico"},
    )
    assert company_response.status_code == 200
    company_id = company_response.json()["id"]

    payload = {
        "source": "99freelas",
        "external_url": (
            "https://example.invalid/99freelas/"
            + scenario["name"]
        ),
        "title": scenario["title"],
        "description": scenario["description"],
        "requirements": scenario["requirements"],
        "budget": scenario["budget"],
        "deadline": scenario["deadline"],
        "captured_at": "2026-10-08T12:00:00-03:00",
    }

    unauthenticated = client.get("/opportunities")
    assert unauthenticated.status_code == 401

    created = client.post(
        "/opportunities",
        headers=operator_a_headers,
        json=payload,
    )
    assert created.status_code == 200
    opportunity = created.json()
    assert opportunity["company_id"] == company_id
    assert opportunity["next_action"] == "pending"

    duplicate = client.post(
        "/opportunities",
        headers=operator_a_headers,
        json=payload,
    )
    assert duplicate.status_code == 409

    triaged = client.patch(
        f"/opportunities/{opportunity['id']}/triage",
        headers=operator_a_headers,
        json={
            "next_action": scenario["next_action"],
            "triage_note": scenario["triage_note"],
        },
    )
    assert triaged.status_code == 200
    assert triaged.json()["next_action"] == scenario["next_action"]
    assert triaged.json()["triage_note"] == scenario["triage_note"]

    listing = client.get("/opportunities", headers=operator_a_headers)
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["id"] == opportunity["id"]

    brief_url = f"/opportunities/{opportunity['id']}/proposal-brief"
    if scenario["next_action"] != "prepare_proposal":
        blocked = client.post(
            brief_url,
            headers=operator_a_headers,
            json=BRIEF,
        )
        assert blocked.status_code == 409
        assert client.get(brief_url, headers=operator_a_headers).status_code == 404
        return

    created_brief = client.post(
        brief_url,
        headers=operator_a_headers,
        json=BRIEF,
    )
    assert created_brief.status_code == 200
    brief = created_brief.json()
    assert brief["opportunity_id"] == opportunity["id"]
    assert brief["status"] == "draft"

    revision = {**BRIEF, "status": "ready_for_review"}
    revised = client.patch(
        brief_url,
        headers=operator_a_headers,
        json=revision,
    )
    assert revised.status_code == 200
    assert revised.json()["status"] == "ready_for_review"
    assert client.get(
        brief_url,
        headers=operator_a_headers,
    ).json()["id"] == brief["id"]

    # Ready for review NAO equivale a aprovacao, precificacao ou envio.
    assert not {"price", "approved", "sent_at"} & revised.json().keys()
    invalid_approval = client.patch(
        brief_url,
        headers=operator_a_headers,
        json={**revision, "status": "approved"},
    )
    assert invalid_approval.status_code == 422

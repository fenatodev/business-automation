"""Company global search endpoint: GET /companies/{id}/search.

Cobre busca global por oportunidades, conversas, leads e customers,
incluindo tenant isolation, autenticação e validação de parâmetros.
"""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Maria"):
    res = client.post(
        "/leads", headers=headers,
        json={"company_id": company_id, "name": name, "phone": "11999999999", "source": "site", "interest": "automacao"},
    )
    assert res.status_code == 200
    return res.json()


def test_global_search_empty(client, admin_headers, operator_a_headers):
    """GET search returns empty results for new company."""
    company = _create_company(client, admin_headers, name="SearchCo")
    res = client.get(
        f"/companies/{company['id']}/search?q=teste",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "opportunities" in data
    assert "conversations" in data
    assert "leads" in data
    assert "customers" in data
    assert data["opportunities"] == []
    assert data["leads"] == []


def test_global_search_finds_lead(client, admin_headers, operator_a_headers):
    """Search finds leads by name."""
    company = _create_company(client, admin_headers, name="LeadSearchCo")
    _create_lead(client, operator_a_headers, company["id"], name="João Silva")

    res = client.get(
        f"/companies/{company['id']}/search?q=João",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["leads"]) >= 1
    assert data["leads"][0]["entity_type"] == "lead"


def test_global_search_finds_opportunity(client, admin_headers, operator_a_headers):
    """Search finds opportunities by title."""
    company = _create_company(client, admin_headers, name="OppSearchCo")
    client.post(
        "/opportunities", headers=operator_a_headers,
        json={
            "source": "manual",
            "external_url": "https://example.com/test",
            "title": "Projeto Automação",
            "description": "Automação de processos",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    res = client.get(
        f"/companies/{company['id']}/search?q=Automação",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["opportunities"]) >= 1
    assert data["opportunities"][0]["entity_type"] == "opportunity"


def test_global_search_limit(client, admin_headers, operator_a_headers):
    """Search respects limit parameter."""
    company = _create_company(client, admin_headers, name="LimitCo")
    for i in range(5):
        _create_lead(client, operator_a_headers, company["id"], name=f"Lead {i}")

    res = client.get(
        f"/companies/{company['id']}/search?q=Lead&limit=2",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert len(res.json()["leads"]) <= 2


def test_global_search_case_insensitive(client, admin_headers, operator_a_headers):
    """Search is case-insensitive."""
    company = _create_company(client, admin_headers, name="CaseCo")
    _create_lead(client, operator_a_headers, company["id"], name="Maria")

    for query in ["maria", "MARIA", "MaRiA"]:
        res = client.get(
            f"/companies/{company['id']}/search?q={query}",
            headers=operator_a_headers,
        )
        assert res.status_code == 200
        assert len(res.json()["leads"]) >= 1


def test_global_search_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot search Operator A's company."""
    company = _create_company(client, admin_headers, name="IsoSearchCo")
    _create_lead(client, operator_a_headers, company["id"], name="Privado")

    res = client.get(
        f"/companies/{company['id']}/search?q=Privado",
        headers=operator_b_headers,
    )
    assert res.status_code == 403


def test_global_search_requires_auth(client, admin_headers, operator_a_headers):
    """GET search without auth returns 401."""
    company = _create_company(client, admin_headers, name="AuthSearchCo")
    res = client.get(f"/companies/{company['id']}/search?q=teste")
    assert res.status_code in (401, 403)


def test_global_search_invalid_query(client, admin_headers, operator_a_headers):
    """Search with empty query returns 422."""
    company = _create_company(client, admin_headers, name="InvalidSearchCo")
    res = client.get(
        f"/companies/{company['id']}/search?q=",
        headers=operator_a_headers,
    )
    assert res.status_code == 422


def test_global_search_nonexistent_company(client, admin_headers, operator_a_headers):
    """Search for nonexistent company returns 404."""
    res = client.get(
        "/companies/99999/search?q=teste",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_global_search_result_format(client, admin_headers, operator_a_headers):
    """Search results contain required fields."""
    company = _create_company(client, admin_headers, name="FormatCo")
    _create_lead(client, operator_a_headers, company["id"], name="Teste")

    res = client.get(
        f"/companies/{company['id']}/search?q=Teste",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    lead = res.json()["leads"][0]
    assert "entity_type" in lead
    assert "entity_id" in lead
    assert "title" in lead
    assert "snippet" in lead

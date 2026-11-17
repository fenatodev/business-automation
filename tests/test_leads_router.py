"""Leads router endpoints: CRUD, count, company-leads, bulk-delete, suggestions.

Cobre os endpoints do leads.py que não têm testes dedicados:
criação, listagem, contagem, detalhe, atualização, leads por company,
bulk delete e sugestões de IA (opportunity e status).
"""
from datetime import datetime, timezone


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Maria", phone="11999999999"):
    res = client.post(
        "/leads", headers=headers,
        json={"company_id": company_id, "name": name, "phone": phone, "source": "site", "interest": "automacao"},
    )
    assert res.status_code == 200
    return res.json()


# --- Create ---


def test_create_lead(client, admin_headers, operator_a_headers):
    """POST /leads creates a new lead with all fields."""
    company = _create_company(client, admin_headers, name="CreateLeadCo")
    res = client.post(
        "/leads", headers=operator_a_headers,
        json={
            "company_id": company["id"],
            "name": "João Silva",
            "phone": "11987654321",
            "source": "instagram",
            "interest": "consultoria",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "João Silva"
    assert data["phone"] == "11987654321"
    assert data["source"] == "instagram"
    assert data["interest"] == "consultoria"
    assert data["status"] == "new"
    assert "id" in data


def test_create_lead_without_interest(client, admin_headers, operator_a_headers):
    """POST /leads works without optional interest field."""
    company = _create_company(client, admin_headers, name="NoInterestCo")
    res = client.post(
        "/leads", headers=operator_a_headers,
        json={
            "company_id": company["id"],
            "name": "Ana",
            "phone": "11911111111",
            "source": "site",
        },
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Ana"


def test_create_lead_requires_auth(client, admin_headers):
    """POST /leads without auth returns 401."""
    company = _create_company(client, admin_headers, name="AuthLeadCo")
    res = client.post(
        "/leads",
        json={
            "company_id": company["id"],
            "name": "Sem Auth",
            "phone": "11922222222",
            "source": "site",
        },
    )
    assert res.status_code in (401, 403)


# --- List ---


def test_list_leads_empty(client, admin_headers, operator_a_headers):
    """GET /leads returns empty list for new company."""
    _create_company(client, admin_headers, name="EmptyListCo")
    res = client.get("/leads", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_leads_returns_created(client, admin_headers, operator_a_headers):
    """GET /leads returns created leads."""
    company = _create_company(client, admin_headers, name="ListCo")
    _create_lead(client, operator_a_headers, company["id"], name="Primeiro")
    res = client.get("/leads", headers=operator_a_headers)
    assert res.status_code == 200
    leads = res.json()
    assert len(leads) >= 1
    assert any(l["name"] == "Primeiro" for l in leads)


def test_list_leads_filter_by_status(client, admin_headers, operator_a_headers):
    """GET /leads?status= filters by status."""
    company = _create_company(client, admin_headers, name="FilterCo")
    _create_lead(client, operator_a_headers, company["id"], name="New1")
    _create_lead(client, operator_a_headers, company["id"], name="New2")

    # Update one to contacted
    lead2 = [l for l in client.get("/leads", headers=operator_a_headers).json()
              if l["name"] == "New2"][0]
    client.patch(
        f"/leads/{lead2['id']}", headers=operator_a_headers,
        json={"status": "contacted"},
    )

    res = client.get("/leads?status=new", headers=operator_a_headers)
    assert res.status_code == 200
    for lead in res.json():
        assert lead["status"] == "new"


def test_list_leads_limit_offset(client, admin_headers, operator_a_headers):
    """GET /leads respects limit and offset parameters."""
    company = _create_company(client, admin_headers, name="PagCo")
    for i in range(5):
        _create_lead(client, operator_a_headers, company["id"], name=f"Pag{i}")

    res = client.get("/leads?limit=2&offset=0", headers=operator_a_headers)
    assert res.status_code == 200
    assert len(res.json()) <= 2


def test_list_leads_requires_auth(client, admin_headers):
    """GET /leads without auth returns 401."""
    res = client.get("/leads")
    assert res.status_code in (401, 403)


# --- Count ---


def test_count_leads(client, admin_headers, operator_a_headers):
    """GET /leads/count returns total count."""
    company = _create_company(client, admin_headers, name="CountCo")
    before = client.get("/leads/count", headers=operator_a_headers).json()
    _create_lead(client, operator_a_headers, company["id"], name="Count1")
    _create_lead(client, operator_a_headers, company["id"], name="Count2")

    res = client.get("/leads/count", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == before["total"] + 2


def test_count_leads_with_status_filter(client, admin_headers, operator_a_headers):
    """GET /leads/count?status= returns filtered count."""
    company = _create_company(client, admin_headers, name="CountFilterCo")
    _create_lead(client, operator_a_headers, company["id"], name="C1")
    _create_lead(client, operator_a_headers, company["id"], name="C2")

    lead = client.get("/leads", headers=operator_a_headers).json()[0]
    client.patch(
        f"/leads/{lead['id']}", headers=operator_a_headers,
        json={"status": "qualified"},
    )

    res = client.get("/leads/count?status=qualified", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["total"] >= 1


# --- Get ---


def test_get_lead(client, admin_headers, operator_a_headers):
    """GET /leads/{id} returns the lead detail."""
    company = _create_company(client, admin_headers, name="GetCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Detalhe")
    res = client.get(f"/leads/{lead['id']}", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == lead["id"]
    assert data["name"] == "Detalhe"


def test_get_lead_not_found(client, admin_headers, operator_a_headers):
    """GET /leads/{id} for nonexistent lead returns 404."""
    _create_company(client, admin_headers, name="NotFoundCo")
    res = client.get("/leads/99999", headers=operator_a_headers)
    assert res.status_code == 404


def test_get_lead_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot get Operator A's lead (returns 404, cross-tenant hidden)."""
    company = _create_company(client, admin_headers, name="IsoGetCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Privado")
    res = client.get(f"/leads/{lead['id']}", headers=operator_b_headers)
    assert res.status_code == 404


# --- Update ---


def test_update_lead_status(client, admin_headers, operator_a_headers):
    """PATCH /leads/{id} updates status."""
    company = _create_company(client, admin_headers, name="UpdateCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Upd")
    res = client.patch(
        f"/leads/{lead['id']}", headers=operator_a_headers,
        json={"status": "contacted"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "contacted"


def test_update_lead_interest(client, admin_headers, operator_a_headers):
    """PATCH /leads/{id} updates interest."""
    company = _create_company(client, admin_headers, name="InterestCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Int")
    res = client.patch(
        f"/leads/{lead['id']}", headers=operator_a_headers,
        json={"interest": "nova interesse"},
    )
    assert res.status_code == 200
    assert res.json()["interest"] == "nova interesse"


def test_update_lead_invalid_status(client, admin_headers, operator_a_headers):
    """PATCH /leads/{id} with invalid status returns 422."""
    company = _create_company(client, admin_headers, name="InvalidCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Inv")
    res = client.patch(
        f"/leads/{lead['id']}", headers=operator_a_headers,
        json={"status": "invalid_status"},
    )
    assert res.status_code == 422


def test_update_lead_not_found(client, admin_headers, operator_a_headers):
    """PATCH /leads/{id} for nonexistent lead returns 404."""
    _create_company(client, admin_headers, name="UpdNotFoundCo")
    res = client.patch(
        "/leads/99999", headers=operator_a_headers,
        json={"status": "contacted"},
    )
    assert res.status_code == 404


def test_update_lead_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot update Operator A's lead (returns 404, cross-tenant hidden)."""
    company = _create_company(client, admin_headers, name="IsoUpdCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Iso")
    res = client.patch(
        f"/leads/{lead['id']}", headers=operator_b_headers,
        json={"status": "won"},
    )
    assert res.status_code == 404


# --- Company leads ---


def test_list_company_leads(client, admin_headers, operator_a_headers):
    """GET /companies/{id}/leads returns leads for that company."""
    company = _create_company(client, admin_headers, name="CompLeadCo")
    _create_lead(client, operator_a_headers, company["id"], name="CL1")
    _create_lead(client, operator_a_headers, company["id"], name="CL2")

    res = client.get(f"/companies/{company['id']}/leads", headers=operator_a_headers)
    assert res.status_code == 200
    leads = res.json()
    assert len(leads) >= 2


def test_list_company_leads_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot list Operator A's company leads."""
    company = _create_company(client, admin_headers, name="CompIsoCo")
    _create_lead(client, operator_a_headers, company["id"], name="CL")
    res = client.get(f"/companies/{company['id']}/leads", headers=operator_b_headers)
    assert res.status_code == 403


# --- Bulk delete ---


def test_bulk_delete_leads(client, admin_headers, operator_a_headers):
    """POST /leads/bulk-delete removes specified leads."""
    company = _create_company(client, admin_headers, name="BulkDelCo")
    lead1 = _create_lead(client, operator_a_headers, company["id"], name="Del1")
    lead2 = _create_lead(client, operator_a_headers, company["id"], name="Del2")

    before = client.get("/leads/count", headers=operator_a_headers).json()["total"]
    res = client.post(
        "/leads/bulk-delete", headers=operator_a_headers,
        json={"lead_ids": [lead1["id"], lead2["id"]]},
    )
    assert res.status_code == 200
    assert res.json()["deleted"] >= 2

    after = client.get("/leads/count", headers=operator_a_headers).json()["total"]
    assert after == before - 2


def test_bulk_delete_empty_list(client, admin_headers, operator_a_headers):
    """POST /leads/bulk-delete with empty list returns 422."""
    _create_company(client, admin_headers, name="BulkEmptyCo")
    res = client.post(
        "/leads/bulk-delete", headers=operator_a_headers,
        json={"lead_ids": []},
    )
    assert res.status_code == 422


def test_bulk_delete_nonexistent_ids(client, admin_headers, operator_a_headers):
    """POST /leads/bulk-delete with nonexistent IDs does not error."""
    company = _create_company(client, admin_headers, name="BulkGhostCo")
    res = client.post(
        "/leads/bulk-delete", headers=operator_a_headers,
        json={"lead_ids": [99998, 99999]},
    )
    assert res.status_code == 200
    assert res.json()["deleted"] == 0


def test_bulk_delete_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B bulk delete with Operator A's lead IDs deletes 0 (tenant-isolated)."""
    company = _create_company(client, admin_headers, name="BulkIsoCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="BID")
    res = client.post(
        "/leads/bulk-delete", headers=operator_b_headers,
        json={"lead_ids": [lead["id"]]},
    )
    assert res.status_code == 200
    assert res.json()["deleted"] == 0


# --- Suggest opportunity from lead ---


def test_suggest_opportunity_from_lead(client, admin_headers, operator_a_headers):
    """POST /leads/{id}/suggest-opportunity returns suggestion or 503."""
    company = _create_company(client, admin_headers, name="SuggestOppCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="Sug")
    res = client.post(
        f"/leads/{lead['id']}/suggest-opportunity",
        headers=operator_a_headers,
    )
    # May return 200 with suggestion or 503 if Ollama unavailable
    assert res.status_code in (200, 503)


def test_suggest_opportunity_from_lead_not_found(client, admin_headers, operator_a_headers):
    """POST /leads/{id}/suggest-opportunity for nonexistent lead returns 404."""
    _create_company(client, admin_headers, name="SugNotFoundCo")
    res = client.post(
        "/leads/99999/suggest-opportunity",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_suggest_opportunity_from_lead_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot suggest opportunity for Operator A's lead (returns 404)."""
    company = _create_company(client, admin_headers, name="SugIsoCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="SugIso")
    res = client.post(
        f"/leads/{lead['id']}/suggest-opportunity",
        headers=operator_b_headers,
    )
    assert res.status_code == 404


# --- Suggest lead status ---


def test_suggest_lead_status(client, admin_headers, operator_a_headers):
    """POST /leads/{id}/suggest-status returns suggestion or 503."""
    company = _create_company(client, admin_headers, name="SugStatusCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="SS")
    res = client.post(
        f"/leads/{lead['id']}/suggest-status",
        headers=operator_a_headers,
    )
    # May return 200 with suggestion or 503 if Ollama unavailable
    assert res.status_code in (200, 503)


def test_suggest_lead_status_not_found(client, admin_headers, operator_a_headers):
    """POST /leads/{id}/suggest-status for nonexistent lead returns 404."""
    _create_company(client, admin_headers, name="SugStatNotFoundCo")
    res = client.post(
        "/leads/99999/suggest-status",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_suggest_lead_status_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot suggest status for Operator A's lead (returns 404)."""
    company = _create_company(client, admin_headers, name="SugStatIsoCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="SSI")
    res = client.post(
        f"/leads/{lead['id']}/suggest-status",
        headers=operator_b_headers,
    )
    assert res.status_code == 404

"""Customers router endpoints: CRUD, count, company-customers, convert-lead, bulk-delete, suggestions.

Cobre os endpoints do customers.py que não têm testes dedicados:
criação, listagem, contagem, detalhe, atualização, conversão de lead,
bulk delete e sugestões de IA (opportunity e lead).
"""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_customer(client, headers, company_id, name="Maria", phone="11999999999", email=None):
    data = {"company_id": company_id, "name": name, "phone": phone}
    if email:
        data["email"] = email
    res = client.post("/customers", headers=headers, json=data)
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


def test_create_customer(client, admin_headers, operator_a_headers):
    """POST /customers creates a new customer with all fields."""
    company = _create_company(client, admin_headers, name="CreateCustCo")
    res = client.post(
        "/customers", headers=operator_a_headers,
        json={
            "company_id": company["id"],
            "name": "João Silva",
            "phone": "11987654321",
            "email": "joao@example.com",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "João Silva"
    assert data["phone"] == "11987654321"
    assert data["email"] == "joao@example.com"
    assert "id" in data


def test_create_customer_without_email(client, admin_headers, operator_a_headers):
    """POST /customers works without optional email field."""
    company = _create_company(client, admin_headers, name="NoEmailCo")
    res = client.post(
        "/customers", headers=operator_a_headers,
        json={
            "company_id": company["id"],
            "name": "Ana",
            "phone": "11911111111",
        },
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Ana"


def test_create_customer_requires_auth(client, admin_headers):
    """POST /customers without auth returns 401."""
    company = _create_company(client, admin_headers, name="AuthCustCo")
    res = client.post(
        "/customers",
        json={
            "company_id": company["id"],
            "name": "Sem Auth",
            "phone": "11922222222",
        },
    )
    assert res.status_code in (401, 403)


# --- List ---


def test_list_customers_empty(client, admin_headers, operator_a_headers):
    """GET /customers returns empty list for new company."""
    _create_company(client, admin_headers, name="EmptyCustCo")
    res = client.get("/customers", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json() == []


def test_list_customers_returns_created(client, admin_headers, operator_a_headers):
    """GET /customers returns created customers."""
    company = _create_company(client, admin_headers, name="ListCustCo")
    _create_customer(client, operator_a_headers, company["id"], name="Primeiro")
    res = client.get("/customers", headers=operator_a_headers)
    assert res.status_code == 200
    customers = res.json()
    assert len(customers) >= 1
    assert any(c["name"] == "Primeiro" for c in customers)


def test_list_customers_search(client, admin_headers, operator_a_headers):
    """GET /customers?q= searches by name."""
    company = _create_company(client, admin_headers, name="SearchCustCo")
    _create_customer(client, operator_a_headers, company["id"], name="Busca Teste")
    res = client.get("/customers?q=Busca", headers=operator_a_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 1


def test_list_customers_limit_offset(client, admin_headers, operator_a_headers):
    """GET /customers respects limit and offset parameters."""
    company = _create_company(client, admin_headers, name="PagCustCo")
    for i in range(5):
        _create_customer(client, operator_a_headers, company["id"], name=f"Cust{i}")

    res = client.get("/customers?limit=2&offset=0", headers=operator_a_headers)
    assert res.status_code == 200
    assert len(res.json()) <= 2


def test_list_customers_requires_auth(client, admin_headers):
    """GET /customers without auth returns 401."""
    res = client.get("/customers")
    assert res.status_code in (401, 403)


# --- Count ---


def test_count_customers(client, admin_headers, operator_a_headers):
    """GET /customers/count returns total count."""
    company = _create_company(client, admin_headers, name="CountCustCo")
    before = client.get("/customers/count", headers=operator_a_headers).json()
    _create_customer(client, operator_a_headers, company["id"], name="C1")
    _create_customer(client, operator_a_headers, company["id"], name="C2")

    res = client.get("/customers/count", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["total"] == before["total"] + 2


# --- Get ---


def test_get_customer(client, admin_headers, operator_a_headers):
    """GET /customers/{id} returns the customer detail."""
    company = _create_company(client, admin_headers, name="GetCustCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="Detalhe")
    res = client.get(f"/customers/{cust['id']}", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == cust["id"]
    assert data["name"] == "Detalhe"


def test_get_customer_not_found(client, admin_headers, operator_a_headers):
    """GET /customers/{id} for nonexistent customer returns 404."""
    _create_company(client, admin_headers, name="NotFoundCustCo")
    res = client.get("/customers/99999", headers=operator_a_headers)
    assert res.status_code == 404


def test_get_customer_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot get Operator A's customer (returns 404, cross-tenant hidden)."""
    company = _create_company(client, admin_headers, name="IsoCustCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="Privado")
    res = client.get(f"/customers/{cust['id']}", headers=operator_b_headers)
    assert res.status_code == 404


# --- Update ---


def test_update_customer_name(client, admin_headers, operator_a_headers):
    """PATCH /customers/{id} updates name."""
    company = _create_company(client, admin_headers, name="UpdCustCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="Original")
    res = client.patch(
        f"/customers/{cust['id']}", headers=operator_a_headers,
        json={"name": "Atualizado"},
    )
    assert res.status_code == 200
    assert res.json()["name"] == "Atualizado"


def test_update_customer_phone(client, admin_headers, operator_a_headers):
    """PATCH /customers/{id} updates phone."""
    company = _create_company(client, admin_headers, name="PhoneCustCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="Phone")
    res = client.patch(
        f"/customers/{cust['id']}", headers=operator_a_headers,
        json={"phone": "11999888777"},
    )
    assert res.status_code == 200
    assert res.json()["phone"] == "11999888777"


def test_update_customer_email(client, admin_headers, operator_a_headers):
    """PATCH /customers/{id} updates email."""
    company = _create_company(client, admin_headers, name="EmailCustCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="Email")
    res = client.patch(
        f"/customers/{cust['id']}", headers=operator_a_headers,
        json={"email": "novo@example.com"},
    )
    assert res.status_code == 200
    assert res.json()["email"] == "novo@example.com"


def test_update_customer_not_found(client, admin_headers, operator_a_headers):
    """PATCH /customers/{id} for nonexistent customer returns 404."""
    _create_company(client, admin_headers, name="UpdNotFoundCustCo")
    res = client.patch(
        "/customers/99999", headers=operator_a_headers,
        json={"name": "Ghost"},
    )
    assert res.status_code == 404


def test_update_customer_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot update Operator A's customer (returns 404)."""
    company = _create_company(client, admin_headers, name="IsoUpdCustCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="Iso")
    res = client.patch(
        f"/customers/{cust['id']}", headers=operator_b_headers,
        json={"name": "Hacked"},
    )
    assert res.status_code == 404


# --- Company customers ---


def test_list_company_customers(client, admin_headers, operator_a_headers):
    """GET /companies/{id}/customers returns customers for that company."""
    company = _create_company(client, admin_headers, name="CompCustCo")
    _create_customer(client, operator_a_headers, company["id"], name="CC1")
    _create_customer(client, operator_a_headers, company["id"], name="CC2")

    res = client.get(f"/companies/{company['id']}/customers", headers=operator_a_headers)
    assert res.status_code == 200
    assert len(res.json()) >= 2


def test_list_company_customers_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot list Operator A's company customers."""
    company = _create_company(client, admin_headers, name="CompIsoCustCo")
    _create_customer(client, operator_a_headers, company["id"], name="CC")
    res = client.get(f"/companies/{company['id']}/customers", headers=operator_b_headers)
    assert res.status_code == 403


# --- Convert lead to customer ---


def test_convert_lead_to_customer(client, admin_headers, operator_a_headers):
    """POST /leads/{id}/convert creates customer from lead."""
    company = _create_company(client, admin_headers, name="ConvertCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="ConvertMe")

    before = client.get("/customers/count", headers=operator_a_headers).json()["total"]
    res = client.post(
        f"/leads/{lead['id']}/convert", headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "ConvertMe"

    after = client.get("/customers/count", headers=operator_a_headers).json()["total"]
    assert after == before + 1


def test_convert_lead_to_customer_not_found(client, admin_headers, operator_a_headers):
    """POST /leads/{id}/convert for nonexistent lead returns 404."""
    _create_company(client, admin_headers, name="ConvertNotFoundCo")
    res = client.post("/leads/99999/convert", headers=operator_a_headers)
    assert res.status_code == 404


def test_convert_lead_to_customer_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot convert Operator A's lead."""
    company = _create_company(client, admin_headers, name="ConvertIsoCo")
    lead = _create_lead(client, operator_a_headers, company["id"], name="ConvIso")
    res = client.post(f"/leads/{lead['id']}/convert", headers=operator_b_headers)
    assert res.status_code == 404


# --- Bulk delete ---


def test_bulk_delete_customers(client, admin_headers, operator_a_headers):
    """POST /customers/bulk-delete removes specified customers."""
    company = _create_company(client, admin_headers, name="BulkDelCustCo")
    c1 = _create_customer(client, operator_a_headers, company["id"], name="Del1")
    c2 = _create_customer(client, operator_a_headers, company["id"], name="Del2")

    before = client.get("/customers/count", headers=operator_a_headers).json()["total"]
    res = client.post(
        "/customers/bulk-delete", headers=operator_a_headers,
        json={"customer_ids": [c1["id"], c2["id"]]},
    )
    assert res.status_code == 200
    assert res.json()["deleted"] >= 2

    after = client.get("/customers/count", headers=operator_a_headers).json()["total"]
    assert after == before - 2


def test_bulk_delete_customers_empty_list(client, admin_headers, operator_a_headers):
    """POST /customers/bulk-delete with empty list returns 422."""
    _create_company(client, admin_headers, name="BulkEmptyCustCo")
    res = client.post(
        "/customers/bulk-delete", headers=operator_a_headers,
        json={"customer_ids": []},
    )
    assert res.status_code == 422


def test_bulk_delete_customers_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B bulk delete with Operator A's customer IDs deletes 0."""
    company = _create_company(client, admin_headers, name="BulkIsoCustCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="BID")
    res = client.post(
        "/customers/bulk-delete", headers=operator_b_headers,
        json={"customer_ids": [cust["id"]]},
    )
    assert res.status_code == 200
    assert res.json()["deleted"] == 0


# --- Suggest opportunity from customer ---


def test_suggest_opportunity_from_customer(client, admin_headers, operator_a_headers):
    """POST /customers/{id}/suggest-opportunity returns suggestion or 503."""
    company = _create_company(client, admin_headers, name="SugOppCustCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="Sug")
    res = client.post(
        f"/customers/{cust['id']}/suggest-opportunity",
        headers=operator_a_headers,
    )
    assert res.status_code in (200, 503)


def test_suggest_opportunity_from_customer_not_found(client, admin_headers, operator_a_headers):
    """POST /customers/{id}/suggest-opportunity for nonexistent customer returns 404."""
    _create_company(client, admin_headers, name="SugOppNotFoundCo")
    res = client.post("/customers/99999/suggest-opportunity", headers=operator_a_headers)
    assert res.status_code == 404


def test_suggest_opportunity_from_customer_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot suggest opportunity for Operator A's customer."""
    company = _create_company(client, admin_headers, name="SugOppIsoCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="SugIso")
    res = client.post(
        f"/customers/{cust['id']}/suggest-opportunity",
        headers=operator_b_headers,
    )
    assert res.status_code == 404


# --- Suggest lead from customer ---


def test_suggest_lead_from_customer(client, admin_headers, operator_a_headers):
    """POST /customers/{id}/suggest-lead returns suggestion or 503."""
    company = _create_company(client, admin_headers, name="SugLeadCustCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="SL")
    res = client.post(
        f"/customers/{cust['id']}/suggest-lead",
        headers=operator_a_headers,
    )
    assert res.status_code in (200, 503)


def test_suggest_lead_from_customer_not_found(client, admin_headers, operator_a_headers):
    """POST /customers/{id}/suggest-lead for nonexistent customer returns 404."""
    _create_company(client, admin_headers, name="SugLeadNotFoundCo")
    res = client.post("/customers/99999/suggest-lead", headers=operator_a_headers)
    assert res.status_code == 404


def test_suggest_lead_from_customer_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot suggest lead for Operator A's customer."""
    company = _create_company(client, admin_headers, name="SugLeadIsoCo")
    cust = _create_customer(client, operator_a_headers, company["id"], name="SLI")
    res = client.post(
        f"/customers/{cust['id']}/suggest-lead",
        headers=operator_b_headers,
    )
    assert res.status_code == 404

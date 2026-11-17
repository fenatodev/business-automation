"""WP-081 — Fechar e reabrir conversas via PATCH.

Testa o backend de atualização de status de conversas: fechar, reabrir,
autenticação, 404, status inválido, tenant isolation, reflexão na lista,
filtro por status e count com filtro.
"""


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


def _create_conv(client, headers, company_id, lead_id, channel="whatsapp"):
    res = client.post(
        "/conversations", headers=headers,
        json={"company_id": company_id, "channel": channel, "lead_id": lead_id},
    )
    assert res.status_code == 200
    return res.json()


def test_close_conversation(client, admin_headers, operator_a_headers):
    """PATCH /conversations/{id} with status=closed closes the conversation."""
    company = _create_company(client, admin_headers, name="CloseCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
    assert conv["status"] == "open"

    res = client.patch(
        f"/conversations/{conv['id']}",
        headers=operator_a_headers,
        json={"status": "closed"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "closed"


def test_reopen_conversation(client, admin_headers, operator_a_headers):
    """PATCH /conversations/{id} with status=open reopens a closed conversation."""
    company = _create_company(client, admin_headers, name="ReopenCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])

    client.patch(f"/conversations/{conv['id']}", headers=operator_a_headers, json={"status": "closed"})
    res = client.patch(
        f"/conversations/{conv['id']}",
        headers=operator_a_headers,
        json={"status": "open"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "open"


def test_close_conversation_requires_auth(client, admin_headers, operator_a_headers):
    """PATCH without auth returns 401."""
    company = _create_company(client, admin_headers, name="AuthCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])

    res = client.patch(f"/conversations/{conv['id']}", json={"status": "closed"})
    assert res.status_code in (401, 403)


def test_close_nonexistent_conversation_returns_404(client, admin_headers, operator_a_headers):
    """PATCH on nonexistent conversation returns 404."""
    res = client.patch(
        "/conversations/99999",
        headers=operator_a_headers,
        json={"status": "closed"},
    )
    assert res.status_code == 404


def test_close_invalid_status_returns_422(client, admin_headers, operator_a_headers):
    """PATCH with invalid status value returns 422."""
    company = _create_company(client, admin_headers, name="InvalidCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])

    res = client.patch(
        f"/conversations/{conv['id']}",
        headers=operator_a_headers,
        json={"status": "invalid_status"},
    )
    assert res.status_code == 422


def test_close_conversation_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot close Operator A's conversation."""
    company_a = _create_company(client, admin_headers, name="TenantA")
    lead_a = _create_lead(client, operator_a_headers, company_a["id"])
    conv_a = _create_conv(client, operator_a_headers, company_a["id"], lead_a["id"])

    res = client.patch(
        f"/conversations/{conv_a['id']}",
        headers=operator_b_headers,
        json={"status": "closed"},
    )
    assert res.status_code == 404  # Cross-tenant returns 404, not 403


def test_close_reflects_in_list(client, admin_headers, operator_a_headers):
    """After closing, the conversation list reflects the new status."""
    company = _create_company(client, admin_headers, name="ListCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])

    client.patch(f"/conversations/{conv['id']}", headers=operator_a_headers, json={"status": "closed"})

    res = client.get(f"/companies/{company['id']}/conversations", headers=operator_a_headers)
    assert res.status_code == 200
    convs = res.json()
    found = [c for c in convs if c["id"] == conv["id"]]
    assert len(found) == 1
    assert found[0]["status"] == "closed"


def test_filter_by_closed_status(client, admin_headers, operator_a_headers):
    """GET /conversations?status=closed returns only closed conversations."""
    company = _create_company(client, admin_headers, name="FilterCo")
    lead1 = _create_lead(client, operator_a_headers, company["id"], name="L1")
    lead2 = _create_lead(client, operator_a_headers, company["id"], name="L2")
    conv1 = _create_conv(client, operator_a_headers, company["id"], lead1["id"])
    conv2 = _create_conv(client, operator_a_headers, company["id"], lead2["id"])

    client.patch(f"/conversations/{conv1['id']}", headers=operator_a_headers, json={"status": "closed"})

    res = client.get(
        f"/companies/{company['id']}/conversations?status=closed",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    closed_convs = res.json()
    assert len(closed_convs) == 1
    assert closed_convs[0]["id"] == conv1["id"]


def test_count_with_status_filter(client, admin_headers, operator_a_headers):
    """Count endpoint respects status filter."""
    company = _create_company(client, admin_headers, name="CountCo")
    lead1 = _create_lead(client, operator_a_headers, company["id"], name="L1")
    lead2 = _create_lead(client, operator_a_headers, company["id"], name="L2")
    conv1 = _create_conv(client, operator_a_headers, company["id"], lead1["id"])
    conv2 = _create_conv(client, operator_a_headers, company["id"], lead2["id"])

    client.patch(f"/conversations/{conv1['id']}", headers=operator_a_headers, json={"status": "closed"})

    res_open = client.get(
        f"/companies/{company['id']}/conversations/count?status=open",
        headers=operator_a_headers,
    )
    assert res_open.status_code == 200
    assert res_open.json()["total"] == 1

    res_closed = client.get(
        f"/companies/{company['id']}/conversations/count?status=closed",
        headers=operator_a_headers,
    )
    assert res_closed.status_code == 200
    assert res_closed.json()["total"] == 1

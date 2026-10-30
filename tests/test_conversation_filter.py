"""Backend tests for WP-078: conversation search and filter.

Validates the optional query parameters (channel, status, q) in
GET /companies/{company_id}/conversations.
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


def _add_message(client, headers, conv_id, sender_type, content):
    res = client.post(
        f"/conversations/{conv_id}/messages", headers=headers,
        json={"sender_type": sender_type, "content": content},
    )
    assert res.status_code == 200
    return res.json()


def test_list_conversations_without_filters(client, admin_headers, operator_a_headers):
    """Listing conversations without filters returns all conversations."""
    company = _create_company(client, admin_headers)
    lead = _create_lead(client, operator_a_headers, company["id"])
    _create_conv(client, operator_a_headers, company["id"], lead["id"])
    res = client.get(f"/companies/{company['id']}/conversations", headers=operator_a_headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)


def test_filter_by_channel(client, admin_headers, operator_a_headers):
    """Filtering by channel returns only matching conversations."""
    company = _create_company(client, admin_headers)
    lead1 = _create_lead(client, operator_a_headers, company["id"], name="L1")
    lead2 = _create_lead(client, operator_a_headers, company["id"], name="L2")
    _create_conv(client, operator_a_headers, company["id"], lead1["id"], channel="whatsapp")
    _create_conv(client, operator_a_headers, company["id"], lead2["id"], channel="web")
    res = client.get(
        f"/companies/{company['id']}/conversations?channel=whatsapp", headers=operator_a_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["channel"] == "whatsapp"


def test_filter_by_status_open(client, admin_headers, operator_a_headers):
    """Filtering by status=open returns all conversations (default status)."""
    company = _create_company(client, admin_headers)
    lead1 = _create_lead(client, operator_a_headers, company["id"], name="L1")
    lead2 = _create_lead(client, operator_a_headers, company["id"], name="L2")
    _create_conv(client, operator_a_headers, company["id"], lead1["id"])
    _create_conv(client, operator_a_headers, company["id"], lead2["id"])
    res = client.get(
        f"/companies/{company['id']}/conversations?status=open", headers=operator_a_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert all(c["status"] == "open" for c in data)


def test_filter_by_status_closed_returns_empty(client, admin_headers, operator_a_headers):
    """Filtering by status=closed returns empty when all are open."""
    company = _create_company(client, admin_headers)
    lead = _create_lead(client, operator_a_headers, company["id"])
    _create_conv(client, operator_a_headers, company["id"], lead["id"])
    res = client.get(
        f"/companies/{company['id']}/conversations?status=closed", headers=operator_a_headers
    )
    assert res.status_code == 200
    assert res.json() == []


def test_filter_by_channel_and_status(client, admin_headers, operator_a_headers):
    """Combining channel and status filters works correctly."""
    company = _create_company(client, admin_headers)
    leads = [_create_lead(client, operator_a_headers, company["id"], name=f"L{i}") for i in range(3)]
    _create_conv(client, operator_a_headers, company["id"], leads[0]["id"], channel="whatsapp")
    _create_conv(client, operator_a_headers, company["id"], leads[1]["id"], channel="whatsapp")
    _create_conv(client, operator_a_headers, company["id"], leads[2]["id"], channel="web")
    # All are status=open by default; filter by whatsapp+open returns 2
    res = client.get(
        f"/companies/{company['id']}/conversations?channel=whatsapp&status=open",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert all(c["channel"] == "whatsapp" for c in data)
    assert all(c["status"] == "open" for c in data)


def test_search_by_keyword_in_messages(client, admin_headers, operator_a_headers):
    """Searching by keyword returns conversations with matching messages."""
    company = _create_company(client, admin_headers)
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
    _add_message(client, operator_a_headers, conv["id"], "customer", "Preciso de orçamento")
    _add_message(client, operator_a_headers, conv["id"], "agent", "Olá, como posso ajudar?")
    res = client.get(
        f"/companies/{company['id']}/conversations?q=orçamento", headers=operator_a_headers
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == conv["id"]


def test_search_keyword_case_insensitive(client, admin_headers, operator_a_headers):
    """Keyword search is case-insensitive (ASCII)."""
    company = _create_company(client, admin_headers)
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
    _add_message(client, operator_a_headers, conv["id"], "customer", "PRECISO DE AJUDA AGORA")
    res = client.get(
        f"/companies/{company['id']}/conversations?q=ajuda", headers=operator_a_headers
    )
    assert res.status_code == 200
    assert len(res.json()) == 1


def test_search_keyword_no_match(client, admin_headers, operator_a_headers):
    """Searching for non-existent keyword returns empty list."""
    company = _create_company(client, admin_headers)
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
    _add_message(client, operator_a_headers, conv["id"], "customer", "Olá")
    res = client.get(
        f"/companies/{company['id']}/conversations?q=xyz123", headers=operator_a_headers
    )
    assert res.status_code == 200
    assert res.json() == []


def test_search_combined_with_channel_filter(client, admin_headers, operator_a_headers):
    """Keyword search combined with channel filter works."""
    company = _create_company(client, admin_headers)
    lead1 = _create_lead(client, operator_a_headers, company["id"], name="L1")
    lead2 = _create_lead(client, operator_a_headers, company["id"], name="L2")
    conv_wa = _create_conv(client, operator_a_headers, company["id"], lead1["id"], channel="whatsapp")
    conv_web = _create_conv(client, operator_a_headers, company["id"], lead2["id"], channel="web")
    _add_message(client, operator_a_headers, conv_wa["id"], "customer", "Preciso de ajuda")
    _add_message(client, operator_a_headers, conv_web["id"], "customer", "Preciso de ajuda")
    res = client.get(
        f"/companies/{company['id']}/conversations?channel=whatsapp&q=ajuda",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["channel"] == "whatsapp"


def test_filter_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Filters respect tenant isolation."""
    company_a = _create_company(client, admin_headers, name="CompanyA")
    company_b = _create_company(client, admin_headers, name="CompanyB")
    lead_b = _create_lead(client, operator_b_headers, company_b["id"])
    _create_conv(client, operator_b_headers, company_b["id"], lead_b["id"], channel="whatsapp")
    res = client.get(
        f"/companies/{company_a['id']}/conversations?channel=whatsapp",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json() == []


def test_filter_requires_auth(client):
    """Filtering requires authentication."""
    res = client.get("/companies/1/conversations?channel=web")
    assert res.status_code in (401, 403)


def test_filter_returns_empty_when_no_match(client, admin_headers, operator_a_headers):
    """Filter returns empty list when no conversations match."""
    company = _create_company(client, admin_headers)
    lead = _create_lead(client, operator_a_headers, company["id"])
    _create_conv(client, operator_a_headers, company["id"], lead["id"], channel="web")
    res = client.get(
        f"/companies/{company['id']}/conversations?channel=telegram", headers=operator_a_headers
    )
    assert res.status_code == 200
    assert res.json() == []


def test_conversation_without_messages_not_returned_in_search(client, admin_headers, operator_a_headers):
    """Conversations without messages are not returned in keyword search."""
    company = _create_company(client, admin_headers)
    lead = _create_lead(client, operator_a_headers, company["id"])
    _create_conv(client, operator_a_headers, company["id"], lead["id"])
    res = client.get(
        f"/companies/{company['id']}/conversations?q=qualquer", headers=operator_a_headers
    )
    assert res.status_code == 200
    assert res.json() == []

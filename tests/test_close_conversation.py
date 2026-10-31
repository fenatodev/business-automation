"""WP-081 — Close conversation endpoint."""


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
    """Closing a conversation changes status to closed."""
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
    """Reopening a closed conversation changes status back to open."""
    company = _create_company(client, admin_headers, name="ReopenCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])

    client.patch(
        f"/conversations/{conv['id']}",
        headers=operator_a_headers,
        json={"status": "closed"},
    )
    res = client.patch(
        f"/conversations/{conv['id']}",
        headers=operator_a_headers,
        json={"status": "open"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "open"


def test_close_conversation_requires_auth(client, admin_headers, operator_a_headers):
    """Closing a conversation requires authentication."""
    company = _create_company(client, admin_headers, name="AuthCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])

    res = client.patch(
        f"/conversations/{conv['id']}",
        json={"status": "closed"},
    )
    assert res.status_code in (401, 403)


def test_close_nonexistent_conversation(client, admin_headers, operator_a_headers):
    """Closing a nonexistent conversation returns 404."""
    res = client.patch(
        "/conversations/99999",
        headers=operator_a_headers,
        json={"status": "closed"},
    )
    assert res.status_code == 404


def test_close_invalid_status(client, admin_headers, operator_a_headers):
    """Invalid status value is rejected."""
    company = _create_company(client, admin_headers, name="InvalidCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])

    res = client.patch(
        f"/conversations/{conv['id']}",
        headers=operator_a_headers,
        json={"status": "archived"},
    )
    assert res.status_code == 422


def test_close_conversation_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot close Operator B's conversation."""
    company_a = _create_company(client, admin_headers, name="TenantACo")
    company_b = _create_company(client, admin_headers, name="TenantBCo")
    lead_b = _create_lead(client, operator_b_headers, company_b["id"])
    conv_b = _create_conv(client, operator_b_headers, company_b["id"], lead_b["id"])

    res = client.patch(
        f"/conversations/{conv_b['id']}",
        headers=operator_a_headers,
        json={"status": "closed"},
    )
    assert res.status_code == 404


def test_close_conversation_reflects_in_list(client, admin_headers, operator_a_headers):
    """Closed conversation shows closed status in list."""
    company = _create_company(client, admin_headers, name="ListCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])

    client.patch(
        f"/conversations/{conv['id']}",
        headers=operator_a_headers,
        json={"status": "closed"},
    )

    res = client.get(
        f"/companies/{company['id']}/conversations",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    found = [c for c in data if c["id"] == conv["id"]]
    assert len(found) == 1
    assert found[0]["status"] == "closed"


def test_filter_closed_conversations(client, admin_headers, operator_a_headers):
    """Filter by status=closed returns only closed conversations."""
    company = _create_company(client, admin_headers, name="FilterCo")
    convs = []
    for i in range(3):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        convs.append(conv)

    # Close only the first conversation
    client.patch(
        f"/conversations/{convs[0]['id']}",
        headers=operator_a_headers,
        json={"status": "closed"},
    )

    res = client.get(
        f"/companies/{company['id']}/conversations?status=closed",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 1
    assert data[0]["id"] == convs[0]["id"]


def test_count_closed_conversations(client, admin_headers, operator_a_headers):
    """Count endpoint respects status filter after closing."""
    company = _create_company(client, admin_headers, name="CountCo")
    convs = []
    for i in range(3):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        convs.append(conv)

    # Close two conversations
    for conv in convs[:2]:
        client.patch(
            f"/conversations/{conv['id']}",
            headers=operator_a_headers,
            json={"status": "closed"},
        )

    res = client.get(
        f"/companies/{company['id']}/conversations/count?status=closed",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["total"] == 2

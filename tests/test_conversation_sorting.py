"""WP-080 — Conversation sorting by last message, created_at, or ID."""
import time


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


def test_default_sort_is_last_message(client, admin_headers, operator_a_headers):
    """Default sort should be last_message (most recent first)."""
    company = _create_company(client, admin_headers, name="SortCo")
    convs = []
    for i in range(3):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        convs.append(conv)
        _add_message(client, operator_a_headers, conv["id"], "customer", f"Msg {i}")
        time.sleep(0.05)

    # Add a later message to the first conversation
    _add_message(client, operator_a_headers, convs[0]["id"], "customer", "Latest message")

    res = client.get(f"/companies/{company['id']}/conversations", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    # convs[0] should be first because it has the latest message
    assert data[0]["id"] == convs[0]["id"]


def test_sort_by_id_ascending(client, admin_headers, operator_a_headers):
    """sort=id returns conversations in ascending ID order."""
    company = _create_company(client, admin_headers, name="SortIdCo")
    convs = []
    for i in range(3):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        convs.append(conv)

    res = client.get(
        f"/companies/{company['id']}/conversations?sort=id",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    ids = [c["id"] for c in data]
    assert ids == sorted(ids)


def test_sort_by_created_at_descending(client, admin_headers, operator_a_headers):
    """sort=created_at returns conversations in descending created_at order."""
    company = _create_company(client, admin_headers, name="SortCreatedCo")
    convs = []
    for i in range(3):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        convs.append(conv)
        time.sleep(1.1)  # SQLite now() has second-level precision

    res = client.get(
        f"/companies/{company['id']}/conversations?sort=created_at",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    # Most recently created should be first
    assert data[0]["id"] == convs[2]["id"]


def test_sort_last_message_with_no_messages(client, admin_headers, operator_a_headers):
    """Conversations without messages should still appear, ordered by ID."""
    company = _create_company(client, admin_headers, name="NoMsgCo")
    convs = []
    for i in range(3):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        convs.append(conv)

    res = client.get(
        f"/companies/{company['id']}/conversations?sort=last_message",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 3
    # All have no messages, so fallback to ID order
    ids = [c["id"] for c in data]
    assert ids == sorted(ids)


def test_sort_last_message_mixed(client, admin_headers, operator_a_headers):
    """Mix of conversations with and without messages — those with messages come first."""
    company = _create_company(client, admin_headers, name="MixedCo")
    convs = []
    for i in range(3):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        convs.append(conv)

    # Only add message to convs[1]
    time.sleep(0.05)
    _add_message(client, operator_a_headers, convs[1]["id"], "customer", "Hello")

    res = client.get(
        f"/companies/{company['id']}/conversations?sort=last_message",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    # convs[1] has a message, should be first
    assert data[0]["id"] == convs[1]["id"]


def test_sort_with_pagination(client, admin_headers, operator_a_headers):
    """Sorting works correctly with pagination."""
    company = _create_company(client, admin_headers, name="PagSortCo")
    convs = []
    for i in range(6):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        convs.append(conv)
        _add_message(client, operator_a_headers, conv["id"], "customer", f"Msg {i}")
        time.sleep(0.05)

    # Add latest message to convs[0]
    _add_message(client, operator_a_headers, convs[0]["id"], "customer", "Latest")

    res = client.get(
        f"/companies/{company['id']}/conversations?sort=last_message&limit=2&offset=0",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    # convs[0] has latest message, should be first
    assert data[0]["id"] == convs[0]["id"]


def test_sort_with_channel_filter(client, admin_headers, operator_a_headers):
    """Sorting works with channel filter."""
    company = _create_company(client, admin_headers, name="FilterSortCo")
    convs = []
    for i in range(4):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        channel = "whatsapp" if i % 2 == 0 else "web"
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"], channel=channel)
        convs.append(conv)
        _add_message(client, operator_a_headers, conv["id"], "customer", f"Msg {i}")
        time.sleep(0.05)

    res = client.get(
        f"/companies/{company['id']}/conversations?channel=whatsapp&sort=last_message",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    for conv in data:
        assert conv["channel"] == "whatsapp"


def test_invalid_sort_defaults_to_id(client, admin_headers, operator_a_headers):
    """Invalid sort value should default to ID ordering."""
    company = _create_company(client, admin_headers, name="InvalidSortCo")
    convs = []
    for i in range(3):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        convs.append(conv)

    res = client.get(
        f"/companies/{company['id']}/conversations?sort=invalid_value",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    ids = [c["id"] for c in data]
    assert ids == sorted(ids)


def test_sort_count_endpoint_unchanged(client, admin_headers, operator_a_headers):
    """Count endpoint should not be affected by sort parameter."""
    company = _create_company(client, admin_headers, name="CountSortCo")
    for i in range(5):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])
        _add_message(client, operator_a_headers, conv["id"], "customer", f"Msg {i}")

    res = client.get(
        f"/companies/{company['id']}/conversations/count",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["total"] == 5

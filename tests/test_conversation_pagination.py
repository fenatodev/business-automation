"""WP-079 — Pagination for conversations endpoint."""


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


def _create_convs(client, admin_headers, operator_a_headers, count=11):
    """Create count conversations with alternating channels."""
    company = _create_company(client, admin_headers, name="PagCo")
    convs = []
    for i in range(count):
        lead = _create_lead(client, operator_a_headers, company["id"], name=f"L{i}")
        channel = "whatsapp" if i % 2 == 0 else "web"
        conv = _create_conv(client, operator_a_headers, company["id"], lead["id"], channel=channel)
        convs.append(conv)
    return company, convs


def test_default_limit_returns_all(client, admin_headers, operator_a_headers):
    """Default limit=50 should return all 11 conversations."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(f"/companies/{company['id']}/conversations", headers=operator_a_headers)
    assert res.status_code == 200
    assert len(res.json()) == 11


def test_limit_param(client, admin_headers, operator_a_headers):
    """limit=3 returns exactly 3 conversations."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(
        f"/companies/{company['id']}/conversations?limit=3&offset=0",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_offset_param(client, admin_headers, operator_a_headers):
    """offset=3 skips the first 3 conversations."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(
        f"/companies/{company['id']}/conversations?limit=3&offset=3",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert len(res.json()) == 3


def test_pagination_pages(client, admin_headers, operator_a_headers):
    """Three pages with limit=5 should have no overlap."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    page1 = client.get(f"/companies/{company['id']}/conversations?limit=5&offset=0", headers=operator_a_headers).json()
    page2 = client.get(f"/companies/{company['id']}/conversations?limit=5&offset=5", headers=operator_a_headers).json()
    page3 = client.get(f"/companies/{company['id']}/conversations?limit=5&offset=10", headers=operator_a_headers).json()
    assert len(page1) == 5
    assert len(page2) == 5
    assert len(page3) == 1
    p1_ids = {c["id"] for c in page1}
    p2_ids = {c["id"] for c in page2}
    p3_ids = {c["id"] for c in page3}
    assert p1_ids.isdisjoint(p2_ids)
    assert p2_ids.isdisjoint(p3_ids)


def test_limit_max_100(client, admin_headers, operator_a_headers):
    """limit=100 is accepted."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(f"/companies/{company['id']}/conversations?limit=100", headers=operator_a_headers)
    assert res.status_code == 200
    assert len(res.json()) == 11


def test_limit_rejected_above_100(client, admin_headers, operator_a_headers):
    """limit=101 is rejected."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(f"/companies/{company['id']}/conversations?limit=101", headers=operator_a_headers)
    assert res.status_code == 422


def test_limit_rejected_below_1(client, admin_headers, operator_a_headers):
    """limit=0 is rejected."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(f"/companies/{company['id']}/conversations?limit=0", headers=operator_a_headers)
    assert res.status_code == 422


def test_offset_negative_rejected(client, admin_headers, operator_a_headers):
    """offset=-1 is rejected."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(f"/companies/{company['id']}/conversations?offset=-1", headers=operator_a_headers)
    assert res.status_code == 422


def test_pagination_with_channel_filter(client, admin_headers, operator_a_headers):
    """Pagination works with channel filter."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(
        f"/companies/{company['id']}/conversations?channel=whatsapp&limit=2&offset=0",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data) <= 2
    for conv in data:
        assert conv["channel"] == "whatsapp"


def test_count_all(client, admin_headers, operator_a_headers):
    """Count endpoint returns total count."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(f"/companies/{company['id']}/conversations/count", headers=operator_a_headers)
    assert res.status_code == 200
    assert res.json()["total"] == 11


def test_count_with_channel_filter(client, admin_headers, operator_a_headers):
    """Count with channel filter returns filtered count."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(
        f"/companies/{company['id']}/conversations/count?channel=whatsapp",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    # 6 whatsapp (indices 0,2,4,6,8,10)
    assert res.json()["total"] == 6


def test_count_zero_when_no_match(client, admin_headers, operator_a_headers):
    """Count returns 0 when no conversations match."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(
        f"/companies/{company['id']}/conversations/count?channel=telegram",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["total"] == 0


def test_count_with_search_filter(client, admin_headers, operator_a_headers):
    """Count with search filter returns matching count."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    for conv in convs:
        _add_message(client, operator_a_headers, conv["id"], "customer", "Preciso de ajuda")
    res = client.get(
        f"/companies/{company['id']}/conversations/count?q=ajuda",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    assert res.json()["total"] == 11


def test_count_requires_auth(client, admin_headers, operator_a_headers):
    """Count endpoint requires authentication."""
    company, convs = _create_convs(client, admin_headers, operator_a_headers)
    res = client.get(f"/companies/{company['id']}/conversations/count")
    assert res.status_code in (401, 403)

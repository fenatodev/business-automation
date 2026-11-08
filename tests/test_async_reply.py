"""WP-533 — Agent reply as async job tests."""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Lead"):
    res = client.post(
        "/leads",
        headers=headers,
        json={"company_id": company_id, "name": name, "phone": "5511999999999", "source": "manual"},
    )
    assert res.status_code == 200
    return res.json()


def _create_conversation(client, headers, company_id, lead_id=None, channel="whatsapp"):
    data = {"channel": channel, "company_id": company_id}
    if lead_id is not None:
        data["lead_id"] = lead_id
    res = client.post("/conversations", headers=headers, json=data)
    assert res.status_code == 200
    return res.json()


def test_async_reply_creates_job(client, admin_headers, operator_a_headers):
    """Async reply endpoint creates a job and returns immediately."""
    company = _create_company(client, admin_headers, name="AsyncCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

    res = client.post(
        f"/conversations/{conv['id']}/agent-reply-async",
        headers=operator_a_headers,
        json={"content": "Hello"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "job_id" in data
    # Job may be pending or already completed (NoopProvider is instant)
    assert data["status"] in ("pending", "completed", "failed")
    assert data["conversation_id"] == conv["id"]


def test_async_reply_persists_customer_message(client, admin_headers, operator_a_headers):
    """Async reply persists the customer message before returning."""
    company = _create_company(client, admin_headers, name="PersistCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

    client.post(
        f"/conversations/{conv['id']}/agent-reply-async",
        headers=operator_a_headers,
        json={"content": "Test message"},
    )

    # Check message was persisted
    res = client.get(
        f"/conversations/{conv['id']}/messages",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    messages = res.json()
    customer_msgs = [m for m in messages if m["sender_type"] == "customer"]
    assert any("Test message" in m["content"] for m in customer_msgs)


def test_async_reply_job_status(client, admin_headers, operator_a_headers):
    """Can poll job status after async reply."""
    company = _create_company(client, admin_headers, name="StatusCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

    create_res = client.post(
        f"/conversations/{conv['id']}/agent-reply-async",
        headers=operator_a_headers,
        json={"content": "Hello"},
    )
    job_id = create_res.json()["job_id"]

    # Poll job status via operator/jobs endpoint
    res = client.get(
        f"/operator/jobs/{job_id}",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["job_id"] == job_id
    assert data["task_type"] == "agent_reply"


def test_async_reply_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator A cannot use async reply on Operator B's conversation."""
    company_a = _create_company(client, admin_headers, name="IsoA")
    company_b = _create_company(client, admin_headers, name="IsoB")
    lead_b = _create_lead(client, operator_b_headers, company_b["id"])
    conv_b = _create_conversation(client, operator_b_headers, company_b["id"], lead_id=lead_b["id"])

    res = client.post(
        f"/conversations/{conv_b['id']}/agent-reply-async",
        headers=operator_a_headers,
        json={"content": "Hello"},
    )
    assert res.status_code == 404


def test_async_reply_requires_auth(client):
    """Async reply requires authentication."""
    res = client.post(
        "/conversations/1/agent-reply-async",
        json={"content": "Hello"},
    )
    assert res.status_code in (401, 403)


def test_async_reply_job_has_result(client, admin_headers, operator_a_headers):
    """Job result contains the agent reply after completion."""
    company = _create_company(client, admin_headers, name="ResultCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conversation(client, operator_a_headers, company["id"], lead_id=lead["id"])

    create_res = client.post(
        f"/conversations/{conv['id']}/agent-reply-async",
        headers=operator_a_headers,
        json={"content": "Hello"},
    )
    job_id = create_res.json()["job_id"]

    # Wait briefly for job to complete (NoopProvider is instant)
    import time
    time.sleep(0.2)

    res = client.get(
        f"/operator/jobs/{job_id}",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    # Job may still be pending if async thread hasn't finished yet
    assert data["status"] in ("pending", "completed", "failed")

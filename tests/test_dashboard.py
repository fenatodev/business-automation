"""WP-082 — Dashboard endpoint aggregates counts across entities."""


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


def _create_opportunity(client, headers, title="Opp"):
    from datetime import datetime, timezone
    res = client.post(
        "/opportunities", headers=headers,
        json={
            "source": "99freelas",
            "external_url": f"https://example.com/{title}",
            "title": title,
            "description": "Test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        },
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


def test_dashboard_returns_all_sections(client, admin_headers, operator_a_headers):
    """Dashboard returns opportunities, conversations, leads, tasks, review_queue."""
    company = _create_company(client, admin_headers, name="DashCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    _create_opportunity(client, operator_a_headers, title="DashOpp")
    _create_conv(client, operator_a_headers, company["id"], lead["id"])

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert "opportunities" in data
    assert "conversations" in data
    assert "leads" in data
    assert "tasks" in data
    assert "review_queue" in data


def test_dashboard_opportunities_count(client, admin_headers, operator_a_headers):
    """Dashboard counts opportunities by next_action."""
    _create_company(client, admin_headers, name="OppDashCo")
    _create_opportunity(client, operator_a_headers, title="Opp1")
    _create_opportunity(client, operator_a_headers, title="Opp2")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["opportunities"]["total"] == 2
    assert data["opportunities"]["pending"] == 2


def test_dashboard_conversations_count(client, admin_headers, operator_a_headers):
    """Dashboard counts conversations by status."""
    company = _create_company(client, admin_headers, name="ConvDashCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    _create_conv(client, operator_a_headers, company["id"], lead["id"])

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["conversations"]["total"] == 1
    assert data["conversations"]["open"] == 1


def test_dashboard_leads_count(client, admin_headers, operator_a_headers):
    """Dashboard counts leads by status."""
    company = _create_company(client, admin_headers, name="LeadDashCo")
    _create_lead(client, operator_a_headers, company["id"], name="L1")
    _create_lead(client, operator_a_headers, company["id"], name="L2")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["leads"]["total"] == 2
    assert data["leads"]["new"] == 2


def test_dashboard_empty_tenant(client, admin_headers, operator_a_headers):
    """Dashboard returns zero counts for empty tenant."""
    _create_company(client, admin_headers, name="EmptyDashCo")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["opportunities"]["total"] == 0
    assert data["conversations"]["total"] == 0
    assert data["leads"]["total"] == 0
    assert data["review_queue"]["total"] == 0


def test_dashboard_requires_auth(client, admin_headers):
    """Dashboard requires authentication."""
    res = client.get("/internal-tasks/dashboard")
    assert res.status_code in (401, 403)


def test_dashboard_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Dashboard only returns counts for the authenticated tenant."""
    company_a = _create_company(client, admin_headers, name="IsolateA")
    company_b = _create_company(client, admin_headers, name="IsolateB")

    lead_a = _create_lead(client, operator_a_headers, company_a["id"], name="LeadA")
    _create_opportunity(client, operator_a_headers, title="IsolateA")
    _create_conv(client, operator_a_headers, company_a["id"], lead_a["id"])

    lead_b = _create_lead(client, operator_b_headers, company_b["id"], name="LeadB")
    _create_opportunity(client, operator_b_headers, title="IsolateB")
    _create_conv(client, operator_b_headers, company_b["id"], lead_b["id"])

    res_a = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    res_b = client.get("/internal-tasks/dashboard", headers=operator_b_headers)
    assert res_a.status_code == 200
    assert res_b.status_code == 200

    data_a = res_a.json()
    data_b = res_b.json()

    # Each tenant sees only their own counts
    assert data_a["leads"]["total"] == 1
    assert data_b["leads"]["total"] == 1
    assert data_a["opportunities"]["total"] == 1
    assert data_b["opportunities"]["total"] == 1


def test_dashboard_opportunity_triage_reflection(client, admin_headers, operator_a_headers):
    """Dashboard reflects opportunity triage changes."""
    _create_company(client, admin_headers, name="TriageDashCo")
    opp = _create_opportunity(client, operator_a_headers, title="TriageOpp")

    # Triage to follow
    res = client.patch(
        f"/opportunities/{opp['id']}/triage", headers=operator_a_headers,
        json={"next_action": "follow"},
    )
    assert res.status_code == 200

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["opportunities"]["follow"] == 1


def test_dashboard_conversation_close_reflection(client, admin_headers, operator_a_headers):
    """Dashboard reflects conversation close status."""
    company = _create_company(client, admin_headers, name="CloseDashCo")
    lead = _create_lead(client, operator_a_headers, company["id"])
    conv = _create_conv(client, operator_a_headers, company["id"], lead["id"])

    # Close the conversation
    res = client.patch(
        f"/conversations/{conv['id']}", headers=operator_a_headers,
        json={"status": "closed"},
    )
    assert res.status_code == 200

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["conversations"]["closed"] == 1


def test_dashboard_tasks_summary_included(client, admin_headers, operator_a_headers):
    """Dashboard includes tasks summary with expected keys."""
    _create_company(client, admin_headers, name="TaskDashCo")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    tasks = data["tasks"]
    assert "queued" in tasks
    assert "running" in tasks
    assert "succeeded" in tasks
    assert "failed" in tasks


def test_dashboard_review_queue_summary_included(client, admin_headers, operator_a_headers):
    """Dashboard includes review_queue summary."""
    _create_company(client, admin_headers, name="RqDashCo")

    res = client.get("/internal-tasks/dashboard", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    rq = data["review_queue"]
    assert "total" in rq

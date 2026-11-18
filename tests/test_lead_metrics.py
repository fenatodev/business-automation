"""Lead metrics endpoints tests.

Tests GET /leads/status-metrics and GET /leads/source-metrics endpoints
that return lead breakdowns for the operator dashboard.
"""


def _create_company(client, admin_headers, name="Company"):
    res = client.post(
        "/companies", headers=admin_headers, json={"name": name, "slug": name.lower()}
    )
    assert res.status_code == 200
    return res.json()


def _create_lead(client, headers, company_id, name="Test Lead", source="manual"):
    res = client.post(
        "/leads",
        headers=headers,
        json={
            "company_id": company_id,
            "name": name,
            "phone": f"+55119{company_id}{source.replace(' ', '')}",
            "source": source,
        },
    )
    assert res.status_code == 200, f"Failed to create lead: {res.text}"
    return res.json()


# --- Status Metrics Tests ---


def test_status_metrics_empty(client, admin_headers, operator_a_headers):
    """Returns zeros when no leads exist."""
    _create_company(client, admin_headers, name="EmptyCo")

    res = client.get("/leads/status-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["by_status"] == []


def test_status_metrics_single_status(client, admin_headers, operator_a_headers):
    """Returns correct count for single status."""
    company = _create_company(client, admin_headers, name="SingleCo")
    _create_lead(client, operator_a_headers, company["id"], name="L1")
    _create_lead(client, operator_a_headers, company["id"], name="L2")

    res = client.get("/leads/status-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["by_status"]) == 1
    assert data["by_status"][0]["status"] == "new"
    assert data["by_status"][0]["count"] == 2


def test_status_metrics_multiple_statuses(client, admin_headers, operator_a_headers):
    """Returns correct breakdown by status."""
    company = _create_company(client, admin_headers, name="MultiStatusCo")

    # Create leads
    l1 = _create_lead(client, operator_a_headers, company["id"], name="L1")
    l2 = _create_lead(client, operator_a_headers, company["id"], name="L2")
    l3 = _create_lead(client, operator_a_headers, company["id"], name="L3")

    # Update statuses
    res = client.patch(
        f"/leads/{l1['id']}",
        headers=operator_a_headers,
        json={"status": "contacted"},
    )
    assert res.status_code == 200

    res = client.patch(
        f"/leads/{l2['id']}",
        headers=operator_a_headers,
        json={"status": "qualified"},
    )
    assert res.status_code == 200

    res = client.get("/leads/status-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 3

    statuses = {item["status"]: item["count"] for item in data["by_status"]}
    assert statuses["new"] == 1
    assert statuses["contacted"] == 1
    assert statuses["qualified"] == 1


def test_status_metrics_sorted_by_count_descending(client, admin_headers, operator_a_headers):
    """Results sorted by count descending."""
    company = _create_company(client, admin_headers, name="SortStatusCo")

    # 3 new leads
    for i in range(3):
        _create_lead(client, operator_a_headers, company["id"], name=f"New{i}")

    # 1 contacted
    l = _create_lead(client, operator_a_headers, company["id"], name="Contacted")
    res = client.patch(
        f"/leads/{l['id']}",
        headers=operator_a_headers,
        json={"status": "contacted"},
    )
    assert res.status_code == 200

    res = client.get("/leads/status-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["by_status"][0]["status"] == "new"
    assert data["by_status"][0]["count"] == 3
    assert data["by_status"][1]["status"] == "contacted"
    assert data["by_status"][1]["count"] == 1


def test_status_metrics_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Status metrics are isolated per tenant."""
    _create_company(client, admin_headers, name="TenantA")
    _create_company(client, admin_headers, name="TenantB")

    # Create leads for company 2 (operator_b)
    for i in range(3):
        _create_lead(client, operator_b_headers, 2, name=f"B{i}")

    res_a = client.get("/leads/status-metrics", headers=operator_a_headers)
    assert res_a.status_code == 200
    assert res_a.json()["total"] == 0

    res_b = client.get("/leads/status-metrics", headers=operator_b_headers)
    assert res_b.status_code == 200
    assert res_b.json()["total"] == 3


def test_status_metrics_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/leads/status-metrics")
    assert res.status_code == 401


# --- Source Metrics Tests ---


def test_source_metrics_empty(client, admin_headers, operator_a_headers):
    """Returns zeros when no leads exist."""
    _create_company(client, admin_headers, name="EmptySourceCo")

    res = client.get("/leads/source-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert data["by_source"] == []


def test_source_metrics_single_source(client, admin_headers, operator_a_headers):
    """Returns correct count for single source."""
    company = _create_company(client, admin_headers, name="SingleSourceCo")
    _create_lead(client, operator_a_headers, company["id"], name="L1", source="manual")
    _create_lead(client, operator_a_headers, company["id"], name="L2", source="manual")

    res = client.get("/leads/source-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 2
    assert len(data["by_source"]) == 1
    assert data["by_source"][0]["source"] == "manual"
    assert data["by_source"][0]["count"] == 2


def test_source_metrics_multiple_sources(client, admin_headers, operator_a_headers):
    """Returns correct breakdown by source."""
    company = _create_company(client, admin_headers, name="MultiSourceCo")

    _create_lead(client, operator_a_headers, company["id"], name="L1", source="manual")
    _create_lead(client, operator_a_headers, company["id"], name="L2", source="manual")
    _create_lead(client, operator_a_headers, company["id"], name="L3", source="99freelas")
    _create_lead(client, operator_a_headers, company["id"], name="L4", source="intake")

    res = client.get("/leads/source-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 4

    sources = {item["source"]: item["count"] for item in data["by_source"]}
    assert sources["manual"] == 2
    assert sources["99freelas"] == 1
    assert sources["intake"] == 1


def test_source_metrics_sorted_by_count_descending(client, admin_headers, operator_a_headers):
    """Results sorted by count descending."""
    company = _create_company(client, admin_headers, name="SortSourceCo")

    # 3 manual leads
    for i in range(3):
        _create_lead(client, operator_a_headers, company["id"], name=f"M{i}", source="manual")

    # 1 intake lead
    _create_lead(client, operator_a_headers, company["id"], name="I1", source="intake")

    res = client.get("/leads/source-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert data["by_source"][0]["source"] == "manual"
    assert data["by_source"][0]["count"] == 3
    assert data["by_source"][1]["source"] == "intake"
    assert data["by_source"][1]["count"] == 1


def test_source_metrics_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Source metrics are isolated per tenant."""
    _create_company(client, admin_headers, name="TenantA")
    _create_company(client, admin_headers, name="TenantB")

    # Create leads for company 2 (operator_b)
    _create_lead(client, operator_b_headers, 2, name="B1", source="manual")

    res_a = client.get("/leads/source-metrics", headers=operator_a_headers)
    assert res_a.status_code == 200
    assert res_a.json()["total"] == 0

    res_b = client.get("/leads/source-metrics", headers=operator_b_headers)
    assert res_b.status_code == 200
    assert res_b.json()["total"] == 1


def test_source_metrics_requires_auth(client):
    """Returns 401 without authentication."""
    res = client.get("/leads/source-metrics")
    assert res.status_code == 401


# --- Response Fields Tests ---


def test_status_metrics_response_fields(client, admin_headers, operator_a_headers):
    """Status metrics response contains all required fields."""
    company = _create_company(client, admin_headers, name="FieldsCo")
    _create_lead(client, operator_a_headers, company["id"], name="L1")

    res = client.get("/leads/status-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert "by_status" in data
    assert "total" in data

    item = data["by_status"][0]
    assert "status" in item
    assert "count" in item


def test_source_metrics_response_fields(client, admin_headers, operator_a_headers):
    """Source metrics response contains all required fields."""
    company = _create_company(client, admin_headers, name="FieldsSourceCo")
    _create_lead(client, operator_a_headers, company["id"], name="L1", source="manual")

    res = client.get("/leads/source-metrics", headers=operator_a_headers)
    assert res.status_code == 200
    data = res.json()

    assert "by_source" in data
    assert "total" in data

    item = data["by_source"][0]
    assert "source" in item
    assert "count" in item

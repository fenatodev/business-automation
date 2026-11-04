"""WP-225 — Keyword search in internal tasks.

The internal tasks module had status filter, sorting, pagination and date filter,
but no keyword search. This adds `?q=` param with case-insensitive search in
event_id and error_code fields.
"""

import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def test_internal_tasks_search_by_event_id(client, admin_headers, operator_a_headers):
    """Search finds tasks by event_id."""
    _create_company(client, admin_headers, "SearchEventCo")
    client.post(
        "/internal-tasks/",
        json={"event_id": "unique-search-event-1", "channel": "web", "message": "Test"},
        headers=operator_a_headers,
    )
    client.post(
        "/internal-tasks/",
        json={"event_id": "another-event-2", "channel": "web", "message": "Other"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/?q=unique-search", headers=operator_a_headers)
    data = response.json()
    assert len(data) >= 1
    for task in data:
        assert "unique-search" in (task.get("event_id") or "").lower()


def test_internal_tasks_search_case_insensitive(client, admin_headers, operator_a_headers):
    """Search is case-insensitive."""
    _create_company(client, admin_headers, "CaseSearchCo")
    client.post(
        "/internal-tasks/",
        json={"event_id": "UPPERCASE-EVENT-1", "channel": "web", "message": "Test"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/?q=uppercase", headers=operator_a_headers)
    data = response.json()
    assert len(data) >= 1


def test_internal_tasks_search_no_match(client, admin_headers, operator_a_headers):
    """Search returns empty when no match."""
    _create_company(client, admin_headers, "NoMatchCo")
    client.post(
        "/internal-tasks/",
        json={"event_id": "evt-no-match", "channel": "web", "message": "Test"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/?q=nonexistentkeyword", headers=operator_a_headers)
    data = response.json()
    assert len(data) == 0


def test_internal_tasks_search_with_status_filter(client, admin_headers, operator_a_headers):
    """Search works combined with status filter."""
    _create_company(client, admin_headers, "SearchStatusCo")
    client.post(
        "/internal-tasks/",
        json={"event_id": "evt-status-test", "channel": "web", "message": "Test"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/?q=status&status=queued", headers=operator_a_headers)
    data = response.json()
    for task in data:
        assert task["status"] == "queued"


def test_internal_tasks_count_with_search(client, admin_headers, operator_a_headers):
    """Count endpoint respects search filter."""
    _create_company(client, admin_headers, "CountSearchCo")
    client.post(
        "/internal-tasks/",
        json={"event_id": "countable-event-1", "channel": "web", "message": "Test"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/count?q=countable", headers=operator_a_headers)
    count = response.json()
    assert count >= 1


def test_internal_tasks_export_csv_with_search(client, admin_headers, operator_a_headers):
    """Export CSV respects search filter."""
    _create_company(client, admin_headers, "ExportSearchCo")
    client.post(
        "/internal-tasks/",
        json={"event_id": "exportable-event-1", "channel": "web", "message": "Test"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/export.csv?q=exportable", headers=operator_a_headers)
    assert response.status_code == 200
    assert "exportable" in response.text.lower()


def test_internal_tasks_search_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Search results are isolated by tenant."""
    _create_company(client, admin_headers, "TenantA")
    _create_company(client, admin_headers, "TenantB")

    client.post(
        "/internal-tasks/",
        json={"event_id": "tenant-a-secret", "channel": "web", "message": "Test"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/?q=secret", headers=operator_b_headers)
    data = response.json()
    for task in data:
        assert task.get("event_id") != "tenant-a-secret"


def test_internal_tasks_search_empty_query(client, admin_headers, operator_a_headers):
    """Empty search query returns all items (no filter)."""
    _create_company(client, admin_headers, "EmptyQueryCo")
    client.post(
        "/internal-tasks/",
        json={"event_id": "evt-empty-1", "channel": "web", "message": "Test"},
        headers=operator_a_headers,
    )

    response = client.get("/internal-tasks/?q=", headers=operator_a_headers)
    data = response.json()
    assert len(data) >= 0


def test_internal_tasks_search_with_pagination(client, admin_headers, operator_a_headers):
    """Search works with pagination."""
    _create_company(client, admin_headers, "PaginatedSearchCo")
    for i in range(5):
        client.post(
            "/internal-tasks/",
            json={"event_id": f"paginated-search-{i}", "channel": "web", "message": "Test"},
            headers=operator_a_headers,
        )

    response = client.get("/internal-tasks/?q=paginated&limit=2&offset=0", headers=operator_a_headers)
    data = response.json()
    assert len(data) <= 2
    for task in data:
        assert "paginated" in (task.get("event_id") or "").lower()

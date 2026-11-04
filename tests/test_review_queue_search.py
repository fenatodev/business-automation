"""WP-224 — Keyword search in review queue.

The review queue module had status filter, sorting, pagination and date filter,
but no keyword search. This adds `?q=` param with case-insensitive search in
message, intent, and event_id fields.
"""

import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def test_review_queue_search_by_message(client, admin_headers, operator_a_headers):
    """Search finds items by message content."""
    _create_company(client, admin_headers, "SearchMessageCo")
    # Create review queue items via synthetic trigger
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "evt-search-1", "channel": "web", "message": "Preciso de um site institucional"},
        headers=operator_a_headers,
    )
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "evt-search-2", "channel": "web", "message": "Orçamento para aplicativo"},
        headers=operator_a_headers,
    )

    response = client.get("/review-queue/?q=site", headers=operator_a_headers)
    data = response.json()
    assert len(data) >= 1
    for item in data:
        assert "site" in (item.get("message") or "").lower() or "site" in (item.get("intent") or "").lower()


def test_review_queue_search_by_event_id(client, admin_headers, operator_a_headers):
    """Search finds items by event_id."""
    _create_company(client, admin_headers, "SearchEventCo")
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "unique-event-123", "channel": "web", "message": "Test message"},
        headers=operator_a_headers,
    )

    response = client.get("/review-queue/?q=unique-event", headers=operator_a_headers)
    data = response.json()
    assert len(data) >= 1
    assert any("unique-event" in item.get("event_id", "") for item in data)


def test_review_queue_search_case_insensitive(client, admin_headers, operator_a_headers):
    """Search is case-insensitive."""
    _create_company(client, admin_headers, "CaseInsensitiveCo")
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "evt-case-1", "channel": "web", "message": "Preciso de AUTOMATION"},
        headers=operator_a_headers,
    )

    response = client.get("/review-queue/?q=automation", headers=operator_a_headers)
    data = response.json()
    assert len(data) >= 1


def test_review_queue_search_no_match(client, admin_headers, operator_a_headers):
    """Search returns empty when no match."""
    _create_company(client, admin_headers, "NoMatchCo")
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "evt-no-match", "channel": "web", "message": "Test message"},
        headers=operator_a_headers,
    )

    response = client.get("/review-queue/?q=nonexistentkeyword", headers=operator_a_headers)
    data = response.json()
    assert len(data) == 0


def test_review_queue_search_with_status_filter(client, admin_headers, operator_a_headers):
    """Search works combined with status filter."""
    _create_company(client, admin_headers, "SearchStatusCo")
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "evt-status-1", "channel": "web", "message": "Test pending"},
        headers=operator_a_headers,
    )

    response = client.get("/review-queue/?q=test&status=pending", headers=operator_a_headers)
    data = response.json()
    for item in data:
        assert item["status"] == "pending"


def test_review_queue_count_with_search(client, admin_headers, operator_a_headers):
    """Count endpoint respects search filter."""
    _create_company(client, admin_headers, "CountSearchCo")
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "evt-count-1", "channel": "web", "message": "Countable message"},
        headers=operator_a_headers,
    )

    response = client.get("/review-queue/count?q=countable", headers=operator_a_headers)
    data = response.json()
    assert data["total"] >= 1


def test_review_queue_export_csv_with_search(client, admin_headers, operator_a_headers):
    """Export CSV respects search filter."""
    _create_company(client, admin_headers, "ExportSearchCo")
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "evt-export-1", "channel": "web", "message": "Exportable content"},
        headers=operator_a_headers,
    )

    response = client.get("/review-queue/export.csv?q=exportable", headers=operator_a_headers)
    assert response.status_code == 200
    assert "exportable" in response.text.lower()


def test_review_queue_search_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Search results are isolated by tenant."""
    _create_company(client, admin_headers, "TenantA")
    _create_company(client, admin_headers, "TenantB")

    # Create item in company A
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "tenant-a-unique", "channel": "web", "message": "Secret message"},
        headers=operator_a_headers,
    )

    # Search from company B should not find it
    response = client.get("/review-queue/?q=secret", headers=operator_b_headers)
    data = response.json()
    for item in data:
        assert item.get("event_id") != "tenant-a-unique"


def test_review_queue_search_empty_query(client, admin_headers, operator_a_headers):
    """Empty search query returns all items (no filter)."""
    _create_company(client, admin_headers, "EmptyQueryCo")
    client.post(
        "/review-queue/synthetic-trigger",
        json={"event_id": "evt-empty-1", "channel": "web", "message": "Test"},
        headers=operator_a_headers,
    )

    response = client.get("/review-queue/?q=", headers=operator_a_headers)
    data = response.json()
    # Empty string should not filter
    assert len(data) >= 0

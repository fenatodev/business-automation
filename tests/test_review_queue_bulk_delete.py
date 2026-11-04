"""WP-230 — Bulk delete review queue items.

The review queue had bulk approve/reject but no bulk delete, making it
impossible to clean up decided items in bulk. This WP adds
POST /review-queue/bulk-delete with tenant isolation.
"""

import pytest


class TestReviewQueueBulkDelete:
    """Test bulk delete of review queue items."""

    def _create_company(self, client, admin_headers, name="TestCo"):
        resp = client.post("/companies", json={
            "name": name,
            "slug": name.lower().replace(" ", "-"),
        }, headers=admin_headers)
        assert resp.status_code == 200, f"Failed to create company: {resp.text}"
        return resp.json()

    def _create_review_item(self, client, operator_headers, company_id, event_id="test-001"):
        resp = client.post("/review-queue/synthetic-trigger", json={
            "channel": "web",
            "message": f"Test message {event_id}",
            "event_id": event_id,
        }, headers=operator_headers)
        assert resp.status_code == 201, f"Failed to create review item: {resp.text}"
        return resp.json()

    def test_bulk_delete_review_items(self, client, admin_headers, operator_a_headers):
        """Bulk delete removes multiple review items."""
        company = self._create_company(client, admin_headers, "BulkDelCo")
        item1 = self._create_review_item(client, operator_a_headers, company["id"], "bulk-del-1")
        item2 = self._create_review_item(client, operator_a_headers, company["id"], "bulk-del-2")

        response = client.post("/review-queue/bulk-delete", json={
            "item_ids": [item1["id"], item2["id"]],
        }, headers=operator_a_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 2
        assert sorted(data["deleted_ids"]) == sorted([item1["id"], item2["id"]])
        assert data["skipped"] == []

    def test_bulk_delete_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Bulk delete cannot delete items from another tenant."""
        company_a = self._create_company(client, admin_headers, "TenantDelA")
        self._create_company(client, admin_headers, "TenantDelB")
        item = self._create_review_item(client, operator_a_headers, company_a["id"], "tenant-del-1")

        response = client.post("/review-queue/bulk-delete", json={
            "item_ids": [item["id"]],
        }, headers=operator_b_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 0
        assert data["skipped"] == [item["id"]]

    def test_bulk_delete_skips_nonexistent(self, client, admin_headers, operator_a_headers):
        """Bulk delete skips IDs that don't exist."""
        self._create_company(client, admin_headers, "SkipDelCo")

        response = client.post("/review-queue/bulk-delete", json={
            "item_ids": [99999, 99998],
        }, headers=operator_a_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 0
        assert sorted(data["skipped"]) == [99998, 99999]

    def test_bulk_delete_mixed(self, client, admin_headers, operator_a_headers):
        """Bulk delete deletes existing items and skips nonexistent ones."""
        company = self._create_company(client, admin_headers, "MixedDelCo")
        item = self._create_review_item(client, operator_a_headers, company["id"], "mixed-del-1")

        response = client.post("/review-queue/bulk-delete", json={
            "item_ids": [item["id"], 99999],
        }, headers=operator_a_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 1
        assert data["deleted_ids"] == [item["id"]]
        assert data["skipped"] == [99999]

    def test_bulk_delete_requires_auth(self, client, admin_headers):
        """Bulk delete requires authentication."""
        response = client.post("/review-queue/bulk-delete", json={
            "item_ids": [1],
        })
        assert response.status_code == 401

    def test_bulk_delete_rejects_empty_list(self, client, admin_headers, operator_a_headers):
        """Bulk delete rejects empty item_ids list."""
        self._create_company(client, admin_headers, "EmptyDelCo")

        response = client.post("/review-queue/bulk-delete", json={
            "item_ids": [],
        }, headers=operator_a_headers)
        assert response.status_code == 422

    def test_bulk_delete_items_actually_removed(self, client, admin_headers, operator_a_headers):
        """Deleted items are no longer returned by list endpoint."""
        company = self._create_company(client, admin_headers, "RemovedDelCo")
        item = self._create_review_item(client, operator_a_headers, company["id"], "removed-del-1")

        client.post("/review-queue/bulk-delete", json={
            "item_ids": [item["id"]],
        }, headers=operator_a_headers)

        response = client.get("/review-queue/", headers=operator_a_headers)
        assert response.status_code == 200
        items = response.json()
        assert not any(i["id"] == item["id"] for i in items)

    def test_bulk_delete_max_100_ids(self, client, admin_headers, operator_a_headers):
        """Bulk delete rejects more than 100 IDs."""
        self._create_company(client, admin_headers, "MaxDelCo")

        response = client.post("/review-queue/bulk-delete", json={
            "item_ids": list(range(1, 102)),
        }, headers=operator_a_headers)
        assert response.status_code == 422

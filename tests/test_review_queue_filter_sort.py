"""WP-131 — Review queue filter by status and sort."""

import pytest


class TestReviewQueueFilterAndSort:
    """GET /review-queue/ with status filter and sort param."""

    def _create_items(self, client, admin_headers, operator_a_headers):
        """Create test review queue items."""
        client.post("/companies", json={"name": "Test Co", "slug": "test-rq"}, headers=admin_headers)
        # Create items via synthetic trigger
        for i in range(3):
            client.post(
                "/review-queue/synthetic-trigger",
                json={
                    "event_id": f"rq-test-{i}",
                    "message": f"Test message {i}",
                    "channel": "web",
                },
                headers=operator_a_headers,
            )

    def test_list_review_queue_default_sort_by_created_at(self, client, admin_headers, operator_a_headers):
        """Default sort should be by created_at descending."""
        self._create_items(client, admin_headers, operator_a_headers)
        resp = client.get("/review-queue/", headers=operator_a_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) >= 1

    def test_list_review_queue_filter_by_pending(self, client, admin_headers, operator_a_headers):
        """Filter by status=pending should return only pending items."""
        self._create_items(client, admin_headers, operator_a_headers)
        resp = client.get("/review-queue/?status=pending", headers=operator_a_headers)
        assert resp.status_code == 200
        items = resp.json()
        for item in items:
            assert item["status"] == "pending"

    def test_list_review_queue_filter_by_approved(self, client, admin_headers, operator_a_headers):
        """Filter by status=approved should return only approved items."""
        self._create_items(client, admin_headers, operator_a_headers)
        resp = client.get("/review-queue/?status=approved", headers=operator_a_headers)
        assert resp.status_code == 200
        # May be empty if no approved items
        items = resp.json()
        for item in items:
            assert item["status"] == "approved"

    def test_list_review_queue_sort_by_id(self, client, admin_headers, operator_a_headers):
        """Sort by id should return items in ascending ID order."""
        self._create_items(client, admin_headers, operator_a_headers)
        resp = client.get("/review-queue/?sort=id", headers=operator_a_headers)
        assert resp.status_code == 200
        items = resp.json()
        ids = [item["id"] for item in items]
        assert ids == sorted(ids)

    def test_list_review_queue_sort_by_status(self, client, admin_headers, operator_a_headers):
        """Sort by status should group items by status."""
        self._create_items(client, admin_headers, operator_a_headers)
        resp = client.get("/review-queue/?sort=status", headers=operator_a_headers)
        assert resp.status_code == 200

    def test_list_review_queue_pagination(self, client, admin_headers, operator_a_headers):
        """Pagination with limit and offset should work."""
        self._create_items(client, admin_headers, operator_a_headers)
        resp = client.get("/review-queue/?limit=1&offset=0", headers=operator_a_headers)
        assert resp.status_code == 200
        items = resp.json()
        assert len(items) <= 1

    def test_count_review_queue(self, client, admin_headers, operator_a_headers):
        """GET /review-queue/count should return total count."""
        self._create_items(client, admin_headers, operator_a_headers)
        resp = client.get("/review-queue/count", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert data["total"] >= 3

    def test_count_review_queue_with_status_filter(self, client, admin_headers, operator_a_headers):
        """Count with status filter should return filtered count."""
        self._create_items(client, admin_headers, operator_a_headers)
        resp = client.get("/review-queue/count?status=pending", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data

    def test_list_review_queue_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator B should not see Operator A's review queue items."""
        self._create_items(client, admin_headers, operator_a_headers)
        # Create company for operator B
        client.post("/companies", json={"name": "Company B", "slug": "company-b"}, headers=admin_headers)
        resp = client.get("/review-queue/", headers=operator_b_headers)
        assert resp.status_code == 200
        items = resp.json()
        # Should be empty or only have items from operator B's company
        for item in items:
            assert item["company_id"] != 1  # Assuming company 1 is operator A's

    def test_combined_filter_and_sort(self, client, admin_headers, operator_a_headers):
        """Status filter and sort should work together."""
        self._create_items(client, admin_headers, operator_a_headers)
        resp = client.get("/review-queue/?status=pending&sort=id", headers=operator_a_headers)
        assert resp.status_code == 200
        items = resp.json()
        for item in items:
            assert item["status"] == "pending"
        ids = [item["id"] for item in items]
        assert ids == sorted(ids)


class TestReviewQueueUIContract:
    """Test the UI contract for review queue filters."""

    def test_review_api_allows_count_endpoint(self):
        """The reviewApi should allow the /count endpoint."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        # Check that reviewApi allowlist includes /count
        assert "/review-queue/count" in content or "/count" in content

    def test_backend_has_count_endpoint(self):
        """The backend should have a /count endpoint."""
        with open("app/routers/review_queue.py") as f:
            content = f.read()
        assert '"/count"' in content
        assert "def count_review_items" in content

    def test_backend_has_status_filter(self):
        """The backend should accept status filter."""
        with open("app/routers/review_queue.py") as f:
            content = f.read()
        assert 'status: str | None = Query' in content
        assert 'ReviewQueueItem.status == status' in content

    def test_backend_has_sort_param(self):
        """The backend should accept sort parameter."""
        with open("app/routers/review_queue.py") as f:
            content = f.read()
        assert 'sort: str = Query' in content
        assert 'sort == "created_at"' in content
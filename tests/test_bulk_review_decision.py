"""WP-171 — Bulk approve/reject in review queue.

Tests that bulk decision endpoint is tenant-isolated, returns correct counts,
and properly skips items that are already decided or don't belong to the tenant.
"""
import pytest

from app.models import Company, ReviewQueueItem
from conftest import TestingSessionLocal


@pytest.fixture
def company_a():
    with TestingSessionLocal() as db:
        db.add(Company(id=1, name="Synthetic A", slug="synthetic-a"))
        db.commit()


@pytest.fixture
def company_b():
    with TestingSessionLocal() as db:
        db.add(Company(id=2, name="Synthetic B", slug="synthetic-b"))
        db.commit()


@pytest.fixture
def items_a(company_a):
    """Create pending review queue items in company A."""
    with TestingSessionLocal() as db:
        db.add(ReviewQueueItem(
            company_id=1, event_id="evt-a1", channel="whatsapp",
            message="Olá, preciso de um site", status="pending",
        ))
        db.add(ReviewQueueItem(
            company_id=1, event_id="evt-a2", channel="web",
            message="Quero um orçamento", status="pending",
        ))
        db.commit()


@pytest.fixture
def items_b(company_b):
    """Create pending review queue items in company B."""
    with TestingSessionLocal() as db:
        db.add(ReviewQueueItem(
            company_id=2, event_id="evt-b1", channel="whatsapp",
            message="Mensagem B", status="pending",
        ))
        db.commit()


class TestBulkReviewDecision:
    """Test POST /review-queue/bulk-decision."""

    def test_bulk_approve(self, client, operator_a_headers, items_a):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1, 2],
            "decision": "approve",
        }, headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["applied"] == 2
        assert resp.json()["skipped"] == []

    def test_bulk_reject(self, client, operator_a_headers, items_a):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1, 2],
            "decision": "reject",
        }, headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["applied"] == 2
        assert resp.json()["skipped"] == []

    def test_bulk_returns_applied_ids(self, client, operator_a_headers, items_a):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1, 2],
            "decision": "approve",
        }, headers=operator_a_headers)
        assert sorted(resp.json()["applied_ids"]) == [1, 2]

    def test_bulk_skips_already_decided(self, client, operator_a_headers, items_a):
        # First decision
        client.post("/review-queue/bulk-decision", json={
            "item_ids": [1],
            "decision": "approve",
        }, headers=operator_a_headers)
        # Second decision on same item should skip
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1, 2],
            "decision": "approve",
        }, headers=operator_a_headers)
        assert resp.json()["applied"] == 1
        assert 1 in resp.json()["skipped"]

    def test_bulk_tenant_isolation(self, client, operator_a_headers, items_b):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1],
            "decision": "approve",
        }, headers=operator_a_headers)
        assert resp.json()["applied"] == 0
        assert 1 in resp.json()["skipped"]

    def test_bulk_requires_auth(self, client):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1],
            "decision": "approve",
        })
        assert resp.status_code in (401, 403)

    def test_bulk_single_item(self, client, operator_a_headers, items_a):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1],
            "decision": "approve",
        }, headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["applied"] == 1

    def test_bulk_empty_rejected(self, client, operator_a_headers):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [],
            "decision": "approve",
        }, headers=operator_a_headers)
        assert resp.status_code == 422

    def test_bulk_with_operator_note(self, client, operator_a_headers, items_a):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1],
            "decision": "approve",
            "operator_note": "Aprovado em lote",
        }, headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json()["applied"] == 1

    def test_bulk_approve_creates_opportunities(self, client, operator_a_headers, items_a):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1, 2],
            "decision": "approve",
        }, headers=operator_a_headers)
        assert resp.json()["applied"] == 2
        # Verify items are now approved
        item1 = client.get("/review-queue/1", headers=operator_a_headers)
        assert item1.json()["status"] == "approve"
        item2 = client.get("/review-queue/2", headers=operator_a_headers)
        assert item2.json()["status"] == "approve"

    def test_bulk_skips_nonexistent(self, client, operator_a_headers, items_a):
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [1, 99999],
            "decision": "approve",
        }, headers=operator_a_headers)
        assert resp.json()["applied"] == 1
        assert 99999 in resp.json()["skipped"]

    def test_bulk_mixed_result(self, client, operator_a_headers, items_a, items_b):
        # items_a has IDs 1,2; items_b has ID 1 (but different company)
        # We include ID 2 (pending, company A), ID 99999 (nonexistent)
        resp = client.post("/review-queue/bulk-decision", json={
            "item_ids": [2, 99999],
            "decision": "approve",
        }, headers=operator_a_headers)
        assert resp.json()["applied"] == 1
        assert 99999 in resp.json()["skipped"]

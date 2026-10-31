"""WP-121 — Review queue CSV export."""

import pytest
from pathlib import Path

from app.models import Company
from app.schemas import ReviewQueueTrigger
from conftest import TestingSessionLocal


@pytest.fixture
def companies():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="rq-a"),
                     Company(id=2, name="Synthetic B", slug="rq-b")])
        db.commit()
        yield


def trigger():
    return ReviewQueueTrigger(event_id="evt-rq-export-001", channel="whatsapp", message="Export test")


class TestReviewQueueExportCSV:
    """GET /review-queue/export.csv endpoint."""

    def test_export_csv_requires_auth(self, client):
        resp = client.get("/review-queue/export.csv")
        assert resp.status_code in (401, 403)

    def test_export_csv_rejects_admin(self, companies, client, admin_headers):
        resp = client.get("/review-queue/export.csv", headers=admin_headers)
        assert resp.status_code == 403

    def test_export_csv_empty(self, companies, client, operator_a_headers):
        resp = client.get("/review-queue/export.csv", headers=operator_a_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "review-queue.csv" in resp.headers["content-disposition"]
        # Should have headers even with no data
        assert "ID" in resp.text
        assert "Evento" in resp.text

    def test_export_csv_with_data(self, companies, client, operator_a_headers):
        payload = trigger().model_dump()
        client.post("/review-queue/synthetic-trigger", json=payload, headers=operator_a_headers)
        resp = client.get("/review-queue/export.csv", headers=operator_a_headers)
        assert resp.status_code == 200
        assert "evt-rq-export-001" in resp.text
        assert "whatsapp" in resp.text

    def test_export_csv_tenant_isolation(self, companies, client, operator_a_headers, operator_b_headers):
        payload = trigger().model_dump()
        client.post("/review-queue/synthetic-trigger", json=payload, headers=operator_a_headers)
        resp = client.get("/review-queue/export.csv", headers=operator_b_headers)
        assert resp.status_code == 200
        # Should not contain data from operator_a's tenant
        assert "evt-rq-export-001" not in resp.text


BASE = Path(__file__).resolve().parent.parent / "app" / "operator_ui"
JS = (BASE / "app.js").read_text()
HTML = (BASE / "index.html").read_text()


class TestReviewQueueExportUI:
    """Review queue export CSV button in the operator UI."""

    def test_html_has_rq_export_csv_button(self):
        assert 'id="rq-export-csv"' in HTML
        assert "Exportar CSV" in HTML

    def test_js_has_rq_export_csv_listener(self):
        assert "rq-export-csv" in JS
        assert "/review-queue/export.csv" in JS

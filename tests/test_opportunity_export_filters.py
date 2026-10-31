"""WP-123 — Filtered opportunity CSV export."""

import pytest
from pathlib import Path


class TestOpportunityExportFilters:
    """GET /opportunities/export.csv with filters."""

    def test_export_csv_accepts_filter_params(self, client, operator_a_headers):
        """The export endpoint accepts all filter query params without error."""
        resp = client.get("/opportunities/export.csv?next_action=pending&q=test&exclude_archived=true",
                          headers=operator_a_headers)
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "ID" in resp.text
        assert "Titulo" in resp.text

    def test_export_csv_accepts_next_action_only(self, client, operator_a_headers):
        """Filtering by next_action alone works."""
        resp = client.get("/opportunities/export.csv?next_action=done", headers=operator_a_headers)
        assert resp.status_code == 200

    def test_export_csv_accepts_search_only(self, client, operator_a_headers):
        """Search filter alone works."""
        resp = client.get("/opportunities/export.csv?q=anything", headers=operator_a_headers)
        assert resp.status_code == 200

    def test_export_csv_accepts_exclude_archived_only(self, client, operator_a_headers):
        """exclude_archived alone works."""
        resp = client.get("/opportunities/export.csv?exclude_archived=true", headers=operator_a_headers)
        assert resp.status_code == 200

    def test_export_csv_returns_csv_headers(self, client, operator_a_headers):
        """Export returns proper CSV headers."""
        resp = client.get("/opportunities/export.csv", headers=operator_a_headers)
        assert resp.status_code == 200
        assert "ID" in resp.text
        assert "Titulo" in resp.text
        assert "Descricao" in resp.text
        assert "Status" in resp.text
        assert "internal-tasks.csv" not in resp.headers.get("content-disposition", "")
        assert "opportunities.csv" in resp.headers.get("content-disposition", "")


BASE = Path(__file__).resolve().parent.parent / "app" / "operator_ui"
JS = (BASE / "app.js").read_text()
HTML = (BASE / "index.html").read_text()


class TestOpportunityExportUI:
    """Opportunity export CSV button in the operator UI."""

    def test_html_has_opp_export_csv_button(self):
        assert 'id="opp-export-csv"' in HTML

    def test_js_has_opp_export_csv_listener(self):
        assert "opp-export-csv" in JS
        assert "/opportunities/export.csv" in JS

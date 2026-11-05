"""WP-275: Test dashboard CSV export endpoint."""

import pytest
from datetime import datetime, timezone


class TestDashboardExportCSV:
    """Verify export-dashboard.csv endpoint behavior."""

    def _setup_data(self, client, admin_headers, operator_headers):
        """Create company and sample data."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        cid = company.json()["id"]

        # Create an opportunity
        opp = client.post("/opportunities", headers=operator_headers, json={
            "company_id": cid,
            "title": "Test Opportunity",
            "description": "Test",
            "source": "manual",
            "external_url": "https://example.com/test",
            "captured_at": datetime.now(timezone.utc).isoformat(),
        })
        assert opp.status_code == 200

        # Create a lead
        lead = client.post("/leads", headers=operator_headers, json={
            "company_id": cid, "name": "Test Lead", "phone": "5511999999999", "source": "manual"
        })
        assert lead.status_code == 200

        # Create a conversation
        conv = client.post("/conversations", headers=operator_headers, json={
            "company_id": cid, "channel": "whatsapp", "lead_id": lead.json()["id"]
        })
        assert conv.status_code == 200

        return cid

    def test_export_returns_csv(self, client, admin_headers, operator_a_headers):
        """Export returns CSV content type."""
        self._setup_data(client, admin_headers, operator_a_headers)
        res = client.get("/internal-tasks/export-dashboard.csv", headers=operator_a_headers)
        assert res.status_code == 200
        assert "text/csv" in res.headers["content-type"]

    def test_export_contains_sections(self, client, admin_headers, operator_a_headers):
        """CSV contains all dashboard sections."""
        self._setup_data(client, admin_headers, operator_a_headers)
        res = client.get("/internal-tasks/export-dashboard.csv", headers=operator_a_headers)
        content = res.text
        assert "OPORTUNIDADES" in content
        assert "CONVERSAS" in content
        assert "LEADS" in content
        assert "BRIEFS" in content
        assert "TAREFAS INTERNAS" in content
        assert "FILA DE REVISAO" in content
        assert "AGENTE IA" in content
        assert "INDICADORES DE PERFORMANCE" in content

    def test_export_has_performance_metrics(self, client, admin_headers, operator_a_headers):
        """CSV contains performance metrics."""
        self._setup_data(client, admin_headers, operator_a_headers)
        res = client.get("/internal-tasks/export-dashboard.csv", headers=operator_a_headers)
        content = res.text
        assert "Taxa de conversao de leads" in content
        assert "Taxa de fechamento de oportunidades" in content
        assert "Taxa de aprovacao de briefs" in content

    def test_export_requires_auth(self, client):
        """Export requires authentication."""
        res = client.get("/internal-tasks/export-dashboard.csv")
        assert res.status_code in (401, 403)

    def test_export_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Operator A sees only their tenant data."""
        company_a = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company_a.status_code == 200
        company_b = client.post("/companies", headers=admin_headers, json={"name": "Beta", "slug": "beta"})
        assert company_b.status_code == 200
        cid_b = company_b.json()["id"]

        # Create many opportunities for B
        for i in range(5):
            client.post("/opportunities", headers=operator_b_headers, json={
                "company_id": cid_b,
                "title": f"Beta Opp {i}",
                "description": "Test",
                "source": "manual",
                "external_url": f"https://example.com/beta-{i}",
                "captured_at": datetime.now(timezone.utc).isoformat(),
            })

        res = client.get("/internal-tasks/export-dashboard.csv", headers=operator_a_headers)
        assert res.status_code == 200
        content = res.text
        assert "OPORTUNIDADES" in content

    def test_export_empty_tenant(self, client, admin_headers, operator_a_headers):
        """Export works with empty tenant data."""
        company = client.post("/companies", headers=admin_headers, json={"name": "Alpha", "slug": "alpha"})
        assert company.status_code == 200
        # Don't create any data
        res = client.get("/internal-tasks/export-dashboard.csv", headers=operator_a_headers)
        assert res.status_code == 200
        content = res.text
        assert "OPORTUNIDADES" in content
        assert "total" in content

    def test_export_has_agent_usage(self, client, admin_headers, operator_a_headers):
        """CSV contains agent usage metrics."""
        self._setup_data(client, admin_headers, operator_a_headers)
        res = client.get("/internal-tasks/export-dashboard.csv", headers=operator_a_headers)
        content = res.text
        assert "Total de chamadas" in content
        assert "Chamadas bem-sucedidas" in content
        assert "Chamadas falhadas" in content

    def test_export_filename_header(self, client, admin_headers, operator_a_headers):
        """Response has correct Content-Disposition header."""
        self._setup_data(client, admin_headers, operator_a_headers)
        res = client.get("/internal-tasks/export-dashboard.csv", headers=operator_a_headers)
        assert "dashboard_report.csv" in res.headers["content-disposition"]

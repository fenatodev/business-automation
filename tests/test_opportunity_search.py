"""WP-094 — Opportunity search backend and UI contract tests."""
from datetime import datetime, timezone

import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, operator_headers, company_id, title="Test Opp", description="Test desc"):
    now = datetime.now(timezone.utc).isoformat()
    res = client.post(
        "/opportunities",
        headers=operator_headers,
        json={
            "source": "99freelas",
            "external_url": f"https://example.com/{title}-{company_id}",
            "title": title,
            "description": description,
            "captured_at": now,
        },
    )
    assert res.status_code == 200
    return res.json()


class TestOpportunitySearchBackend:
    """Verify ?q= search filters opportunities by title and description."""

    def test_search_by_title(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_opportunity(client, operator_a_headers, 1, "Site institucional", "Web dev")
        _create_opportunity(client, operator_a_headers, 1, "App mobile", "Mobile dev")
        res = client.get("/opportunities?q=institucional", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["title"] == "Site institucional"

    def test_search_by_description(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_opportunity(client, operator_a_headers, 1, "Projeto A", "Automação de processos")
        _create_opportunity(client, operator_a_headers, 1, "Projeto B", "Desenvolvimento web")
        res = client.get("/opportunities?q=automação", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["title"] == "Projeto A"

    def test_search_case_insensitive(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_opportunity(client, operator_a_headers, 1, "API REST", "Backend")
        res = client.get("/opportunities?q=api", headers=operator_a_headers)
        assert res.status_code == 200
        assert len(res.json()) == 1
        res2 = client.get("/opportunities?q=API", headers=operator_a_headers)
        assert res2.status_code == 200
        assert len(res2.json()) == 1

    def test_search_no_match(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_opportunity(client, operator_a_headers, 1, "Test", "Desc")
        res = client.get("/opportunities?q=xyz123", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_search_combined_with_exclude_archived(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_opportunity(client, operator_a_headers, 1, "Test Ativo", "Active")
        opp = _create_opportunity(client, operator_a_headers, 1, "Test Finalizado", "Done")
        client.patch(
            f"/opportunities/{opp['id']}",
            headers=operator_a_headers,
            json={"title": "Test Finalizado"},
        )
        # Set to done via triage
        client.patch(
            f"/opportunities/{opp['id']}/triage",
            headers=operator_a_headers,
            json={"next_action": "done"},
        )
        res = client.get("/opportunities?q=Test&exclude_archived=true", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Ativo"

    def test_search_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        _create_opportunity(client, operator_a_headers, 1, "Secret", "Private")
        res = client.get("/opportunities?q=Secret", headers=operator_b_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_search_requires_auth(self, client):
        res = client.get("/opportunities?q=test")
        assert res.status_code in (401, 403)

    def test_backend_has_q_param(self):
        """Verify the backend code has the q parameter."""
        import pathlib
        code = (pathlib.Path("app/routers/opportunities.py")).read_text()
        assert "q: str | None" in code
        assert "func.lower" in code


class TestOpportunitySearchUI:
    """Verify the search field is present in the operator UI."""

    @pytest.fixture
    def operator_ui(self):
        import pathlib
        base = pathlib.Path("app/operator_ui")
        return {
            "html": (base / "index.html").read_text(),
            "js": (base / "app.js").read_text(),
            "css": (base / "styles.css").read_text(),
        }

    def test_opp_search_input_exists(self, operator_ui):
        assert 'id="opp-search"' in operator_ui["html"]

    def test_opp_search_placeholder(self, operator_ui):
        assert "Buscar oportunidades" in operator_ui["html"]

    def test_opp_search_inline_class(self, operator_ui):
        assert "opp-search-inline" in operator_ui["html"]

    def test_opp_search_listener(self, operator_ui):
        js = operator_ui["js"]
        assert '"opp-search"' in js
        assert 'addEventListener("input"' in js

    def test_refresh_list_uses_search(self, operator_ui):
        js = operator_ui["js"]
        assert 'encodeURIComponent' in js
        assert '"q="' in js or "'q='" in js

    def test_opp_search_css(self, operator_ui):
        assert ".opp-search-inline" in operator_ui["css"]

    def test_opp_toolbar_right_css(self, operator_ui):
        assert ".opp-toolbar-right" in operator_ui["css"]

    def test_wp094_comment_in_js(self, operator_ui):
        assert "WP-094" in operator_ui["js"]

    def test_wp094_comment_in_css(self, operator_ui):
        assert "WP-094" in operator_ui["css"]

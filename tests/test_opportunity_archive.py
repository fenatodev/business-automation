"""WP-090 — Opportunity archive filter backend tests."""
from datetime import datetime, timezone

import pytest


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def _create_opportunity(client, operator_headers, company_id, next_action="pending"):
    now = datetime.now(timezone.utc).isoformat()
    res = client.post(
        "/opportunities",
        headers=operator_headers,
        json={
            "source": "99freelas",
            "external_url": f"https://example.com/{next_action}-{company_id}",
            "title": f"Opp {next_action}",
            "description": "Test",
            "captured_at": now,
        },
    )
    assert res.status_code == 200
    opp = res.json()
    # Set the next_action via triage
    if next_action != "pending":
        # done/lost require in_progress first
        if next_action in ("done", "lost"):
            client.patch(
                f"/opportunities/{opp['id']}/triage",
                headers=operator_headers,
                json={"next_action": "in_progress"},
            )
        triage_res = client.patch(
            f"/opportunities/{opp['id']}/triage",
            headers=operator_headers,
            json={"next_action": next_action},
        )
        assert triage_res.status_code == 200
    return opp


class TestExcludeArchivedFilter:
    """Verify exclude_archived query param filters done/lost opportunities."""

    def test_list_without_filter_returns_all(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for action in ["pending", "follow", "in_progress", "done", "lost"]:
            _create_opportunity(client, operator_a_headers, 1, action)
        resp = client.get("/opportunities", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_list_exclude_archived_hides_done_lost(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for action in ["pending", "follow", "in_progress", "done", "lost"]:
            _create_opportunity(client, operator_a_headers, 1, action)
        resp = client.get("/opportunities?exclude_archived=true", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        actions = [o["next_action"] for o in data]
        assert "done" not in actions
        assert "lost" not in actions
        assert "pending" in actions
        assert "follow" in actions
        assert "in_progress" in actions
        assert len(data) == 3

    def test_list_exclude_archived_false_returns_all(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        for action in ["pending", "follow", "in_progress", "done", "lost"]:
            _create_opportunity(client, operator_a_headers, 1, action)
        resp = client.get("/opportunities?exclude_archived=false", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 5

    def test_exclude_archived_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        _create_opportunity(client, operator_a_headers, 1, "done")
        resp = client.get("/opportunities?exclude_archived=true", headers=operator_b_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_exclude_archived_requires_auth(self, client):
        resp = client.get("/opportunities?exclude_archived=true")
        assert resp.status_code in (401, 403)

    def test_backend_has_exclude_archived_param(self):
        """Verify the backend code has the exclude_archived parameter."""
        import pathlib
        code = (pathlib.Path("app/routers/opportunities.py")).read_text()
        assert "exclude_archived" in code
        assert 'notin_(["done", "lost"])' in code


class TestOpportunityArchiveUI:
    """Verify the archive toggle is present in the operator UI."""

    @pytest.fixture
    def operator_ui(self):
        import pathlib
        base = pathlib.Path("app/operator_ui")
        return {
            "html": (base / "index.html").read_text(),
            "js": (base / "app.js").read_text(),
            "css": (base / "styles.css").read_text(),
        }

    def test_show_archived_checkbox_exists(self, operator_ui):
        assert 'id="show-archived"' in operator_ui["html"]

    def test_archive_toggle_label(self, operator_ui):
        assert "Exibir arquivadas" in operator_ui["html"]

    def test_opp_toolbar_class(self, operator_ui):
        assert 'class="opp-toolbar"' in operator_ui["html"]

    def test_refresh_list_uses_exclude_archived(self, operator_ui):
        js = operator_ui["js"]
        assert "exclude_archived" in js

    def test_show_archived_change_listener(self, operator_ui):
        js = operator_ui["js"]
        assert '"show-archived"' in js
        assert 'addEventListener("change"' in js

    def test_allowlist_accepts_exclude_archived(self, operator_ui):
        js = operator_ui["js"]
        # The allowlist regex should accept the query param
        assert "exclude_archived=true" in js

    def test_opp_toolbar_css(self, operator_ui):
        assert ".opp-toolbar" in operator_ui["css"]

    def test_opp_archive_toggle_css(self, operator_ui):
        assert ".opp-archive-toggle" in operator_ui["css"]

    def test_wp090_comment_in_js(self, operator_ui):
        assert "WP-090" in operator_ui["js"]

    def test_wp090_comment_in_css(self, operator_ui):
        assert "WP-090" in operator_ui["css"]

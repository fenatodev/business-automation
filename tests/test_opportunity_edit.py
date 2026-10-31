"""WP-093 — Edit opportunity title and description tests."""
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


class TestUpdateOpportunityBackend:
    """Verify PATCH /opportunities/{id} updates title and description."""

    def test_update_title(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        opp = _create_opportunity(client, operator_a_headers, 1)
        res = client.patch(
            f"/opportunities/{opp['id']}",
            headers=operator_a_headers,
            json={"title": "Novo título"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Novo título"
        assert data["description"] == "Test desc"

    def test_update_description(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        opp = _create_opportunity(client, operator_a_headers, 1)
        res = client.patch(
            f"/opportunities/{opp['id']}",
            headers=operator_a_headers,
            json={"description": "Nova descrição detalhada"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Test Opp"
        assert data["description"] == "Nova descrição detalhada"

    def test_update_both_title_and_description(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        opp = _create_opportunity(client, operator_a_headers, 1)
        res = client.patch(
            f"/opportunities/{opp['id']}",
            headers=operator_a_headers,
            json={"title": "Título completo", "description": "Descrição completa"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Título completo"
        assert data["description"] == "Descrição completa"

    def test_update_empty_body_no_change(self, client, admin_headers, operator_a_headers):
        """Empty body should return the opportunity unchanged."""
        _create_company(client, admin_headers, "Alpha")
        opp = _create_opportunity(client, operator_a_headers, 1)
        res = client.patch(
            f"/opportunities/{opp['id']}",
            headers=operator_a_headers,
            json={},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["title"] == "Test Opp"
        assert data["description"] == "Test desc"

    def test_update_requires_auth(self, client):
        res = client.patch("/opportunities/999", json={"title": "X"})
        assert res.status_code in (401, 403)

    def test_update_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        opp = _create_opportunity(client, operator_a_headers, 1)
        res = client.patch(
            f"/opportunities/{opp['id']}",
            headers=operator_b_headers,
            json={"title": "Hack"},
        )
        assert res.status_code == 404

    def test_update_not_found(self, client, admin_headers, operator_a_headers):
        _create_company(client, admin_headers, "Alpha")
        res = client.patch(
            "/opportunities/99999",
            headers=operator_a_headers,
            json={"title": "X"},
        )
        assert res.status_code == 404

    def test_update_title_max_length(self, client, admin_headers, operator_a_headers):
        """Title over 200 chars should be rejected."""
        _create_company(client, admin_headers, "Alpha")
        opp = _create_opportunity(client, operator_a_headers, 1)
        res = client.patch(
            f"/opportunities/{opp['id']}",
            headers=operator_a_headers,
            json={"title": "A" * 201},
        )
        assert res.status_code == 422

    def test_update_title_empty_string_rejected(self, client, admin_headers, operator_a_headers):
        """Empty string title should be rejected (min_length=1)."""
        _create_company(client, admin_headers, "Alpha")
        opp = _create_opportunity(client, operator_a_headers, 1)
        res = client.patch(
            f"/opportunities/{opp['id']}",
            headers=operator_a_headers,
            json={"title": ""},
        )
        assert res.status_code == 422

    def test_update_reflected_in_list(self, client, admin_headers, operator_a_headers):
        """Updated title should appear in GET /opportunities list."""
        _create_company(client, admin_headers, "Alpha")
        opp = _create_opportunity(client, operator_a_headers, 1)
        client.patch(
            f"/opportunities/{opp['id']}",
            headers=operator_a_headers,
            json={"title": "Atualizado"},
        )
        res = client.get("/opportunities", headers=operator_a_headers)
        assert res.status_code == 200
        data = res.json()
        found = [o for o in data if o["id"] == opp["id"]]
        assert len(found) == 1
        assert found[0]["title"] == "Atualizado"


class TestOpportunityEditUI:
    """Verify the edit panel is present in the operator UI."""

    @pytest.fixture
    def operator_ui(self):
        import pathlib
        base = pathlib.Path("app/operator_ui")
        return {
            "html": (base / "index.html").read_text(),
            "js": (base / "app.js").read_text(),
            "css": (base / "styles.css").read_text(),
        }

    def test_edit_title_input_exists(self, operator_ui):
        assert 'id="edit-title"' in operator_ui["html"]

    def test_edit_description_textarea_exists(self, operator_ui):
        assert 'id="edit-description"' in operator_ui["html"]

    def test_save_edit_button_exists(self, operator_ui):
        assert 'id="save-edit-button"' in operator_ui["html"]

    def test_opp_edit_panel_exists(self, operator_ui):
        assert 'id="opp-edit-panel"' in operator_ui["html"]

    def test_save_edit_listener(self, operator_ui):
        js = operator_ui["js"]
        assert '"save-edit-button"' in js
        assert 'addEventListener("click"' in js

    def test_patch_opportunities_in_js(self, operator_ui):
        js = operator_ui["js"]
        assert 'method: "PATCH"' in js
        assert '"/opportunities/"' in js

    def test_edit_panel_css(self, operator_ui):
        assert ".opp-edit-panel" in operator_ui["css"]

    def test_wp093_comment_in_js(self, operator_ui):
        assert "WP-093" in operator_ui["js"]

    def test_wp093_comment_in_html(self, operator_ui):
        assert "WP-093" in operator_ui["html"]

    def test_wp093_comment_in_css(self, operator_ui):
        assert "WP-093" in operator_ui["css"]

    def test_clear_selection_clears_edit_fields(self, operator_ui):
        js = operator_ui["js"]
        assert '"edit-title"' in js
        assert '"edit-description"' in js

    def test_select_opportunity_populates_edit_fields(self, operator_ui):
        js = operator_ui["js"]
        # selectOpportunity should set .value on edit fields
        assert '$("edit-title").value' in js
        assert '$("edit-description").value' in js

"""WP-264: Test reply templates — reusable responses for the operator."""

import pytest

from app.routers import companies


@pytest.fixture(autouse=True)
def _clear_template_store():
    """Clear the in-memory template store before each test."""
    companies._reply_template_store.clear()
    companies._reply_template_next_id = 1


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


class TestReplyTemplateList:
    """Verify GET /companies/{id}/reply-templates."""

    def test_list_empty_by_default(self, client, admin_headers, operator_a_headers):
        """New company has no templates."""
        _create_company(client, admin_headers, "Alpha")
        res = client.get("/companies/1/reply-templates", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json() == []

    def test_list_returns_templates(self, client, admin_headers, operator_a_headers):
        """List returns created templates."""
        _create_company(client, admin_headers, "Alpha")
        client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "Saudação", "content": "Olá! Como posso ajudar?"},
        )
        res = client.get("/companies/1/reply-templates", headers=operator_a_headers)
        assert res.status_code == 200
        templates = res.json()
        assert len(templates) == 1
        assert templates[0]["name"] == "Saudação"
        assert templates[0]["content"] == "Olá! Como posso ajudar?"

    def test_list_requires_auth(self, client):
        """List requires authentication."""
        res = client.get("/companies/1/reply-templates")
        assert res.status_code in (401, 403)

    def test_list_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Templates are isolated by company."""
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "Template A", "content": "Content A"},
        )
        res = client.get("/companies/2/reply-templates", headers=operator_b_headers)
        assert res.status_code == 200
        assert res.json() == []


class TestReplyTemplateCreate:
    """Verify POST /companies/{id}/reply-templates."""

    def test_create_template(self, client, admin_headers, operator_a_headers):
        """Create a new reply template."""
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "Saudação", "content": "Olá! Como posso ajudar?"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["name"] == "Saudação"
        assert data["content"] == "Olá! Como posso ajudar?"
        assert "id" in data

    def test_create_multiple_templates(self, client, admin_headers, operator_a_headers):
        """Create multiple templates with unique IDs."""
        _create_company(client, admin_headers, "Alpha")
        res1 = client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "T1", "content": "C1"},
        )
        res2 = client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "T2", "content": "C2"},
        )
        assert res1.status_code == 200
        assert res2.status_code == 200
        assert res1.json()["id"] != res2.json()["id"]

    def test_create_requires_name(self, client, admin_headers, operator_a_headers):
        """Name is required."""
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"content": "Sem nome"},
        )
        assert res.status_code == 422

    def test_create_requires_content(self, client, admin_headers, operator_a_headers):
        """Content is required."""
        _create_company(client, admin_headers, "Alpha")
        res = client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "Sem conteúdo"},
        )
        assert res.status_code == 422

    def test_create_requires_auth(self, client):
        """Create requires authentication."""
        res = client.post(
            "/companies/1/reply-templates",
            json={"name": "T", "content": "C"},
        )
        assert res.status_code in (401, 403)

    def test_create_tenant_isolation(self, client, admin_headers, operator_a_headers, operator_b_headers):
        """Templates are isolated by company."""
        _create_company(client, admin_headers, "Alpha")
        _create_company(client, admin_headers, "Beta")
        res = client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "Template A", "content": "Content A"},
        )
        assert res.status_code == 200
        # Operator B cannot create for company A
        res = client.post(
            "/companies/1/reply-templates",
            headers=operator_b_headers,
            json={"name": "Template B", "content": "Content B"},
        )
        assert res.status_code == 403


class TestReplyTemplateDelete:
    """Verify DELETE /companies/{id}/reply-templates/{template_id}."""

    def test_delete_template(self, client, admin_headers, operator_a_headers):
        """Delete an existing template."""
        _create_company(client, admin_headers, "Alpha")
        create_res = client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "T1", "content": "C1"},
        )
        template_id = create_res.json()["id"]
        res = client.delete(f"/companies/1/reply-templates/{template_id}", headers=operator_a_headers)
        assert res.status_code == 200
        assert res.json()["deleted"] is True

    def test_delete_removes_from_list(self, client, admin_headers, operator_a_headers):
        """Deleted template no longer appears in list."""
        _create_company(client, admin_headers, "Alpha")
        create_res = client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "T1", "content": "C1"},
        )
        template_id = create_res.json()["id"]
        client.delete(f"/companies/1/reply-templates/{template_id}", headers=operator_a_headers)
        res = client.get("/companies/1/reply-templates", headers=operator_a_headers)
        assert res.status_code == 200
        assert len(res.json()) == 0

    def test_delete_nonexistent_template(self, client, admin_headers, operator_a_headers):
        """Delete nonexistent template returns 404."""
        _create_company(client, admin_headers, "Alpha")
        res = client.delete("/companies/1/reply-templates/999", headers=operator_a_headers)
        assert res.status_code == 404

    def test_delete_requires_auth(self, client):
        """Delete requires authentication."""
        res = client.delete("/companies/1/reply-templates/1")
        assert res.status_code in (401, 403)

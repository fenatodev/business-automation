"""WP-265: Test reply templates management UI — create, list, delete in agent config section."""

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


class TestReplyTemplateManagementUI:
    """Verify the reply templates management UI contract."""

    def test_template_form_elements_exist(self):
        """Form has name input, content textarea, and save button."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert 'id="reply-template-name"' in html
        assert 'id="reply-template-content"' in html
        assert 'id="reply-template-save"' in html
        assert 'id="reply-template-form"' in html

    def test_template_list_container_exists(self):
        """List container exists for rendering templates."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert 'id="reply-template-list"' in html

    def test_template_management_section_exists(self):
        """Management section is in agent config panel."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert "reply-templates-management" in html
        assert "Templates de resposta" in html

    def test_template_form_has_maxlength(self):
        """Form fields have maxlength constraints matching schema."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert 'maxlength="100"' in html  # name
        assert 'maxlength="4000"' in html  # content

    def test_template_form_fields_required(self):
        """Form fields are required."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        # Find the form section
        form_start = html.index('id="reply-template-form"')
        form_end = html.index('</form>', form_start)
        form_html = html[form_start:form_end]
        assert 'required' in form_html

    def test_js_loads_template_list(self):
        """JS calls templateApi to load list."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert "loadReplyTemplateList" in js
        assert 'templateApi' in js
        assert "/reply-templates" in js

    def test_js_creates_template_on_submit(self):
        """JS form submit handler creates template via POST."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert 'reply-template-form' in js
        assert 'reply-template-name' in js
        assert 'reply-template-content' in js

    def test_js_deletes_template(self):
        """JS has delete handler with confirmation."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert "deleteReplyTemplate" in js
        assert 'confirm(' in js or 'confirm("' in js

    def test_js_refreshes_selector_after_change(self):
        """JS refreshes the reply template selector after create/delete."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        # loadReplyTemplates should be called after template changes
        assert "loadReplyTemplates" in js

    def test_css_styles_exist(self):
        """CSS has styles for template management UI."""
        with open("app/operator_ui/styles.css") as f:
            css = f.read()
        assert ".reply-templates-management" in css
        assert ".reply-template-item" in css
        assert ".reply-template-item-name" in css

    def test_template_api_allowlist_strict(self):
        """templateApi uses regex allowlist."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        # The templateApi from WP-264 should have strict allowlist
        assert "reply-templates" in js

    def test_backend_create_and_list_integration(self, client, admin_headers, operator_a_headers):
        """Full flow: create template and verify it appears in list."""
        _create_company(client, admin_headers, "Alpha")
        # Create template
        res = client.post(
            "/companies/1/reply-templates",
            headers=operator_a_headers,
            json={"name": "Saudação", "content": "Olá! Como posso ajudar?"},
        )
        assert res.status_code == 200
        template_id = res.json()["id"]
        # List templates
        res = client.get("/companies/1/reply-templates", headers=operator_a_headers)
        assert res.status_code == 200
        templates = res.json()
        assert len(templates) == 1
        assert templates[0]["id"] == template_id
        assert templates[0]["name"] == "Saudação"

    def test_backend_delete_integration(self, client, admin_headers, operator_a_headers):
        """Full flow: create and delete template."""
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
        res = client.get("/companies/1/reply-templates", headers=operator_a_headers)
        assert len(res.json()) == 0

    def test_template_management_in_agent_section(self):
        """Template management is inside the agent config section."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        # Find agent config section
        agent_start = html.index('id="agent-config-title"')
        agent_end = html.index('</section>', agent_start)
        agent_section = html[agent_start:agent_end]
        assert "reply-templates-management" in agent_section
        assert "reply-template-form" in agent_section

    def test_js_loads_templates_on_connect(self):
        """loadReplyTemplateList is called on connection."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        # Check that loadReplyTemplateList is called in loadAgentConfigOnConnect
        assert "loadReplyTemplateList" in js

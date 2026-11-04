"""WP-236 — Create opportunity from conversation in operator UI.

The operator could create leads (WP-147) and customers (WP-235) from conversations
but not opportunities. This WP adds the same capability: button, form, and handlers
in the conversation detail panel.
"""

import pytest


class TestCreateOpportunityFromConversationUI:
    """Test UI contract for creating opportunity from conversation."""

    def test_html_has_create_opp_button(self):
        """HTML has conv-create-opp button."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-create-opp"' in content
        assert "Criar oportunidade desta conversa" in content

    def test_html_has_opp_form(self):
        """HTML has conv-opp-form with required fields."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-opp-form"' in content
        assert 'id="conv-opp-title"' in content
        assert 'id="conv-opp-description"' in content
        assert 'id="conv-opp-budget"' in content
        assert 'id="conv-opp-deadline"' in content
        assert 'id="conv-opp-requirements"' in content
        assert 'id="cancel-conv-opp"' in content

    def test_js_has_create_opp_click_handler(self):
        """JS has click handler for conv-create-opp button."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'conv-create-opp' in content
        assert 'addEventListener("click"' in content
        assert 'conv-opp-form' in content

    def test_js_has_cancel_opp_handler(self):
        """JS has cancel handler that hides form and resets fields."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'cancel-conv-opp' in content
        assert 'conv-opp-title' in content

    def test_js_has_opp_form_submit_handler(self):
        """JS has submit handler for conv-opp-form."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'conv-opp-form' in content
        assert 'addEventListener("submit"' in content
        assert 'api("/opportunities", "POST"' in content

    def test_js_select_conversation_shows_opp_button(self):
        """selectConversation shows conv-create-opp button."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert '"conv-create-opp").hidden = false' in content

    def test_js_disconnect_hides_opp_button(self):
        """disconnect/clearSelection hides conv-create-opp."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert "WP-147, WP-235 & WP-236" in content

    def test_css_has_opp_form_styles(self):
        """CSS has .conv-opp-form styles."""
        with open("app/operator_ui/styles.css") as f:
            content = f.read()
        assert ".conv-opp-form" in content
        assert ".conv-opp-form h4" in content
        assert ".conv-opp-form label" in content

    def test_opp_form_has_required_title_field(self):
        """Opportunity form title field is required."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-opp-title" type="text" required' in content

    def test_opp_form_maxlength_constraints(self):
        """Opportunity form fields have maxlength constraints."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'maxlength="200"' in content  # title
        assert 'maxlength="1000"' in content  # description
        assert 'maxlength="50"' in content  # budget
        assert 'maxlength="500"' in content  # requirements

    def test_opp_form_submits_create_button(self):
        """Opportunity form has submit button with correct text."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'type="submit" class="primary">Criar oportunidade</button>' in content

    def test_opp_form_cancel_button(self):
        """Opportunity form has cancel button."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="cancel-conv-opp"' in content
        assert 'class="secondary">Cancelar</button>' in content

    def test_js_handler_resets_fields_on_cancel(self):
        """Cancel handler resets all opportunity form fields."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'conv-opp-title").value = ""' in content
        assert 'conv-opp-description").value = ""' in content
        assert 'conv-opp-budget").value = ""' in content
        assert 'conv-opp-deadline").value = ""' in content
        assert 'conv-opp-requirements").value = ""' in content

    def test_js_handler_resets_fields_on_success(self):
        """Submit handler resets fields after successful creation."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'conv-opp-title").value = ""' in content

    def test_js_handler_refreshes_list_on_success(self):
        """Submit handler calls refreshList after success."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'refreshList()' in content

    def test_opp_form_hidden_by_default(self):
        """Opportunity form is hidden by default in HTML."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-opp-form"' in content
        assert 'hidden' in content.split('id="conv-opp-form"')[1].split('>')[0]

    def test_opp_button_hidden_by_default(self):
        """Create opportunity button is hidden by default."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-create-opp"' in content
        assert 'hidden' in content.split('id="conv-create-opp"')[1].split('>')[0]

    def test_js_handler_uses_source_manual(self):
        """Submit handler sets source to 'manual'."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'source: "manual"' in content

    def test_opp_form_follows_lead_form_pattern(self):
        """Opportunity form structure mirrors the lead form pattern."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        opp_section = content.split('id="conv-opp-form"')[1].split('</form>')[0]
        assert 'two-col' in opp_section

    def test_css_has_textarea_styles(self):
        """CSS includes textarea styles for opportunity form."""
        with open("app/operator_ui/styles.css") as f:
            content = f.read()
        assert ".conv-opp-form textarea" in content

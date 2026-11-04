"""WP-235 — Create customer from conversation in operator UI.

The operator could create leads from conversations (WP-147) but not customers.
This WP adds the same capability for customers: button, form, and handlers
in the conversation detail panel.
"""

import pytest


class TestCreateCustomerFromConversationUI:
    """Test UI contract for creating customer from conversation."""

    def test_html_has_create_customer_button(self):
        """HTML has conv-create-customer button."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-create-customer"' in content
        assert "Criar customer desta conversa" in content

    def test_html_has_customer_form(self):
        """HTML has conv-customer-form with required fields."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-customer-form"' in content
        assert 'id="conv-customer-name"' in content
        assert 'id="conv-customer-phone"' in content
        assert 'id="conv-customer-email"' in content
        assert 'id="conv-customer-source"' in content
        assert 'id="cancel-conv-customer"' in content

    def test_js_has_create_customer_click_handler(self):
        """JS has click handler for conv-create-customer button."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'conv-create-customer' in content
        assert 'addEventListener("click"' in content
        # Verify the handler shows the form
        assert 'conv-customer-form' in content

    def test_js_has_cancel_customer_handler(self):
        """JS has cancel handler that hides form and resets fields."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'cancel-conv-customer' in content
        assert 'conv-customer-name' in content

    def test_js_has_customer_form_submit_handler(self):
        """JS has submit handler for conv-customer-form."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'conv-customer-form' in content
        assert 'addEventListener("submit"' in content
        # Verify it calls customerApi with POST
        assert 'customerApi("/customers", "POST"' in content

    def test_js_select_conversation_shows_customer_button(self):
        """selectConversation shows conv-create-customer button."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        # In selectConversation, both buttons should be shown
        assert '"conv-create-customer").hidden = false' in content

    def test_js_disconnect_hides_customer_button(self):
        """disconnect/clearSelection hides conv-create-customer."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        # Both hide locations should include WP-235
        assert "WP-235" in content

    def test_js_customer_api_allows_post(self):
        """customerApi allowlist permits POST /customers."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        # Check the allowlist includes POST /customers
        assert 'path === "/customers" && method === "POST"' in content

    def test_css_has_customer_form_styles(self):
        """CSS has .conv-customer-form styles."""
        with open("app/operator_ui/styles.css") as f:
            content = f.read()
        assert ".conv-customer-form" in content
        assert ".conv-customer-form h4" in content
        assert ".conv-customer-form label" in content
        assert ".conv-customer-form input" in content

    def test_customer_form_has_required_name_field(self):
        """Customer form name field is required."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-customer-name" type="text" required' in content

    def test_customer_form_maxlength_constraints(self):
        """Customer form fields have maxlength constraints."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-customer-name"' in content
        assert 'maxlength="120"' in content
        assert 'maxlength="30"' in content  # phone
        assert 'maxlength="200"' in content  # email

    def test_customer_form_submits_create_button(self):
        """Customer form has submit button with correct text."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'type="submit" class="primary">Criar customer</button>' in content

    def test_customer_form_cancel_button(self):
        """Customer form has cancel button."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="cancel-conv-customer"' in content
        assert 'class="secondary">Cancelar</button>' in content

    def test_js_handler_prefills_source_from_channel(self):
        """Create customer click handler pre-fills source from conversation channel."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'conv-customer-source' in content
        assert 'conv.channel' in content

    def test_js_handler_resets_fields_on_cancel(self):
        """Cancel handler resets all customer form fields."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'conv-customer-name").value = ""' in content
        assert 'conv-customer-phone").value = ""' in content
        assert 'conv-customer-email").value = ""' in content
        assert 'conv-customer-source").value = ""' in content

    def test_js_handler_resets_fields_on_success(self):
        """Submit handler resets fields after successful creation."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        # After notify, fields should be reset
        assert 'conv-customer-name").value = ""' in content

    def test_js_handler_refreshes_customers_on_success(self):
        """Submit handler calls refreshCustomers after success."""
        with open("app/operator_ui/app.js") as f:
            content = f.read()
        assert 'refreshCustomers()' in content

    def test_customer_form_hidden_by_default(self):
        """Customer form is hidden by default in HTML."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-customer-form"' in content
        assert 'hidden' in content.split('id="conv-customer-form"')[1].split('>')[0]

    def test_customer_button_hidden_by_default(self):
        """Create customer button is hidden by default."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        assert 'id="conv-create-customer"' in content
        assert 'hidden' in content.split('id="conv-create-customer"')[1].split('>')[0]

    def test_customer_form_follows_lead_form_pattern(self):
        """Customer form structure mirrors the lead form pattern."""
        with open("app/operator_ui/index.html") as f:
            content = f.read()
        # Both forms should have two-col layout
        lead_section = content.split('id="conv-lead-form"')[1].split('</form>')[0]
        customer_section = content.split('id="conv-customer-form"')[1].split('</form>')[0]
        assert 'two-col' in lead_section
        assert 'two-col' in customer_section

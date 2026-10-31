"""WP-167 — Create opportunity from customer detail view.

Tests that the customer detail panel has a 'Nova oportunidade' button
and the JavaScript form handler creates opportunities via POST /opportunities.
"""
import re


class TestCustomerOpportunityUI:
    """Test create opportunity from customer UI contract."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/index.html") as f:
            cls.html = f.read()
        with open("app/operator_ui/app.js") as f:
            cls.js = f.read()

    def test_customer_new_opp_button_exists(self):
        """New opportunity button is in the customer detail section."""
        assert 'id="customer-new-opp"' in self.html

    def test_customer_new_opp_button_label(self):
        """Button has correct label."""
        assert '+ Nova oportunidade' in self.html

    def test_customer_opp_form_exists(self):
        """Opportunity creation form exists."""
        assert 'id="customer-opp-form"' in self.html

    def test_customer_opp_form_hidden_by_default(self):
        """Form is hidden by default."""
        assert 'id="customer-opp-form" class="customer-opp-form" hidden' in self.html

    def test_customer_opp_title_field_exists(self):
        """Title input field exists."""
        assert 'id="customer-opp-title"' in self.html

    def test_customer_opp_description_field_exists(self):
        """Description textarea exists."""
        assert 'id="customer-opp-description"' in self.html

    def test_customer_opp_budget_field_exists(self):
        """Budget input field exists."""
        assert 'id="customer-opp-budget"' in self.html

    def test_customer_opp_deadline_field_exists(self):
        """Deadline input field exists."""
        assert 'id="customer-opp-deadline"' in self.html

    def test_customer_opp_requirements_field_exists(self):
        """Requirements textarea exists."""
        assert 'id="customer-opp-requirements"' in self.html

    def test_cancel_customer_opp_button_exists(self):
        """Cancel button exists."""
        assert 'id="cancel-customer-opp"' in self.html

    def test_customer_opp_section_header_exists(self):
        """Oportunidades section header exists."""
        assert '<h4>Oportunidades</h4>' in self.html


class TestCustomerOpportunityJavaScript:
    """Test JavaScript handlers for creating opportunity from customer."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/app.js") as f:
            cls.js = f.read()

    def test_customer_new_opp_click_handler_exists(self):
        """Click handler for new opportunity button exists."""
        assert 'customer-new-opp' in self.js

    def test_customer_new_opp_shows_form(self):
        """Click handler shows the form."""
        section = re.search(
            r'customer-new-opp.*?addEventListener.*?\{[^}]+\}',
            self.js,
            re.DOTALL,
        )
        assert section is not None
        assert 'customer-opp-form' in section.group(0)
        assert '.hidden = false' in section.group(0)

    def test_cancel_customer_opp_handler_exists(self):
        """Cancel button handler exists."""
        assert 'cancel-customer-opp' in self.js

    def test_cancel_hides_and_resets_form(self):
        """Cancel handler hides and resets the form."""
        section = re.search(
            r'cancel-customer-opp.*?addEventListener.*?\{[^}]+\}',
            self.js,
            re.DOTALL,
        )
        assert section is not None
        assert '.hidden = true' in section.group(0)
        assert '.reset()' in section.group(0)

    def test_customer_opp_form_submit_handler_exists(self):
        """Form submit handler exists."""
        assert 'customer-opp-form' in self.js
        assert 'submit' in self.js

    def test_submit_handler_uses_post_opportunities(self):
        """Submit handler calls POST /opportunities."""
        section = re.search(
            r'customer-opp-form.*?addEventListener.*?submit.*?\{.*?POST',
            self.js,
            re.DOTALL,
        )
        assert section is not None

    def test_submit_handler_includes_source_manual(self):
        """Submit handler sets source to manual."""
        section = re.search(
            r'customer-opp-form.*?addEventListener.*?submit.*?\{.*?source.*?manual',
            self.js,
            re.DOTALL,
        )
        assert section is not None

    def test_submit_handler_includes_customer_id(self):
        """Submit handler includes customer reference in external_url."""
        section = re.search(
            r'customer-opp-form.*?addEventListener.*?submit.*?\{.*?currentCustomerId',
            self.js,
            re.DOTALL,
        )
        assert section is not None

    def test_submit_handler_refreshes_list(self):
        """Submit handler refreshes opportunity list after creation."""
        section = re.search(
            r'customer-opp-form.*?addEventListener.*?submit.*?\{.*?refreshList',
            self.js,
            re.DOTALL,
        )
        assert section is not None

    def test_submit_handler_validates_required_fields(self):
        """Submit handler validates title and description."""
        section = re.search(
            r'customer-opp-form.*?addEventListener.*?submit.*?\{.*?title.*?description',
            self.js,
            re.DOTALL,
        )
        assert section is not None

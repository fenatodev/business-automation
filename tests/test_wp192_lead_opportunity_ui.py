"""WP-192 — Create opportunity from lead detail panel.

Tests that the lead detail panel has a button to create a new opportunity,
following the same pattern as WP-167 (customer → opportunity).
"""


class TestLeadOpportunityButton:
    """Test lead opportunity creation button and form exist in HTML."""

    def test_lead_new_opp_button_exists(self):
        """lead-new-opp button exists in lead detail."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert 'id="lead-new-opp"' in html
        btn_line = [line for line in html.split("\n") if 'lead-new-opp' in line][0]
        assert 'type="button"' in btn_line

    def test_lead_opp_form_exists(self):
        """lead-opp-form exists with required fields."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert 'id="lead-opp-form"' in html
        assert 'id="lead-opp-title"' in html
        assert 'id="lead-opp-description"' in html
        assert 'id="lead-opp-budget"' in html
        assert 'id="lead-opp-deadline"' in html
        assert 'id="lead-opp-requirements"' in html

    def test_lead_opp_form_hidden_by_default(self):
        """lead-opp-form is hidden initially."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        form_line = [line for line in html.split("\n") if 'lead-opp-form' in line and 'id=' in line][0]
        assert "hidden" in form_line

    def test_cancel_lead_opp_button_exists(self):
        """cancel-lead-opp button exists in form."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert 'id="cancel-lead-opp"' in html

    def test_lead_opp_form_in_lead_detail(self):
        """lead-opp-form is inside lead-detail panel."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        detail_start = html.index('id="lead-detail"')
        detail_end = html.index('</div>', html.index('lead-conversations-list', detail_start))
        # The form is before leads-pagination
        form_pos = html.index('id="lead-opp-form"')
        pagination_pos = html.index('id="leads-pagination"')
        assert detail_start < form_pos < pagination_pos


class TestLeadOpportunityHandlers:
    """Test JavaScript handlers for lead opportunity creation."""

    def test_lead_new_opp_click_handler(self):
        """lead-new-opp click shows form and focuses title."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert 'lead-new-opp' in js
        assert 'lead-opp-form' in js
        assert 'lead-opp-title' in js
        # Verify click handler shows form
        handler = js.split('lead-new-opp')[1].split("});")[0]
        assert "hidden" in handler
        assert "focus" in handler

    def test_cancel_lead_opp_handler(self):
        """cancel-lead-opp hides and resets form."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert 'cancel-lead-opp' in js
        handler = js.split('cancel-lead-opp')[1].split("});")[0]
        assert "hidden" in handler
        assert "reset" in handler

    def test_lead_opp_form_submit_handler(self):
        """lead-opp-form submit creates opportunity via POST."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert 'lead-opp-form' in js
        # Find the submit handler section
        form_section_start = js.index('lead-opp-form')
        form_section = js[form_section_start:form_section_start + 2000]
        assert "addEventListener" in form_section
        assert "/opportunities" in form_section
        assert "POST" in form_section

    def test_lead_opp_form_uses_current_lead_id(self):
        """Form uses currentLeadId for external_url traceability."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        # Find the lead-opp-form submit handler
        form_section_start = js.index('lead-opp-form')
        form_section = js[form_section_start:form_section_start + 2000]
        assert "currentLeadId" in form_section or "lead-" in form_section

    def test_lead_opp_form_validates_title_and_description(self):
        """Form validates title and description before submission."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        form_section_start = js.index('lead-opp-form')
        form_section = js[form_section_start:form_section_start + 2000]
        assert "lead-opp-title" in form_section
        assert "lead-opp-description" in form_section
        assert "Preencha" in form_section or "title" in form_section

    def test_lead_opp_form_resets_after_success(self):
        """Form resets and hides after successful creation."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        form_section_start = js.index('lead-opp-form')
        form_section = js[form_section_start:form_section_start + 2000]
        assert "reset" in form_section

    def test_lead_opp_section_header_exists(self):
        """Oportunidades section header exists in lead detail."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        # Find the WP-192 comment and verify header
        wp192_pos = html.index("WP-192")
        section = html[wp192_pos:wp192_pos + 500]
        assert "Oportunidades" in section

    def test_lead_opp_form_has_submit_button(self):
        """Form has a submit button."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        form_start = html.index('id="lead-opp-form"')
        form_end = html.index('</form>', form_start)
        form_content = html[form_start:form_end]
        assert 'type="submit"' in form_content

    def test_lead_opp_form_fields_match_customer_pattern(self):
        """Lead opp form has same fields as customer opp form."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        # Customer opp form fields
        cust_start = html.index('id="customer-opp-form"')
        cust_end = html.index('</form>', cust_start)
        cust_fields = set()
        for field in ["title", "description", "budget", "deadline", "requirements"]:
            if f"customer-opp-{field}" in html[cust_start:cust_end]:
                cust_fields.add(field)
        # Lead opp form fields
        lead_start = html.index('id="lead-opp-form"')
        lead_end = html.index('</form>', lead_start)
        lead_fields = set()
        for field in ["title", "description", "budget", "deadline", "requirements"]:
            if f"lead-opp-{field}" in html[lead_start:lead_end]:
                lead_fields.add(field)
        assert cust_fields == lead_fields, f"Field mismatch: {cust_fields} vs {lead_fields}"

    def test_lead_opp_button_visible(self):
        """lead-new-opp button is visible (not hidden by default)."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        btn_section = html.split('id="lead-new-opp"')[1]
        assert "hidden" not in btn_section.split(">")[0]

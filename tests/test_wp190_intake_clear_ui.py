"""WP-190 — Intake form clear button and source labels.

Tests that the intake form has a clear button that resets fields
and hides the decision panel, and that source labels are defined.
"""


class TestIntakeClearButton:
    """Test intake clear button exists and is wired correctly."""

    def test_intake_clear_button_exists(self):
        """intake-clear button exists in HTML."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        assert 'id="intake-clear"' in html
        # The full button line contains type="button" before id
        btn_line = [line for line in html.split("\n") if 'intake-clear' in line][0]
        assert 'type="button"' in btn_line

    def test_intake_clear_handler_exists(self):
        """intake-clear click handler resets form and hides decision."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert 'intake-clear' in js
        assert 'intake-form' in js
        assert 'intake-decision' in js
        # Verify the handler resets form and hides decision
        assert "$('intake-clear')" in js or '$("intake-clear")' in js

    def test_source_labels_defined(self):
        """sourceLabels map covers all known sources."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert "sourceLabels" in js
        # Check key sources are labeled
        assert "manual" in js
        assert "intake" in js
        assert "review_queue" in js
        assert "import" in js

    def test_source_labels_used_in_detail(self):
        """selected-source uses sourceLabels for display."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        # Find the line that sets selected-source
        assert "sourceLabels[record.source]" in js

    def test_intake_clear_button_visible(self):
        """Clear button is visible (not hidden by default)."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        clear_section = html.split('id="intake-clear"')[1]
        assert "hidden" not in clear_section.split(">")[0]

    def test_intake_clear_button_text(self):
        """Clear button has appropriate label."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        clear_section = html.split('id="intake-clear"')[1]
        assert "Limpar" in clear_section.split(">")[1]

    def test_intake_clear_in_form(self):
        """Clear button is inside the intake form."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        form_start = html.index('id="intake-form"')
        form_end = html.index("</form>", form_start)
        clear_pos = html.index('id="intake-clear"')
        assert form_start < clear_pos < form_end

    def test_intake_clear_resets_form(self):
        """Clear handler calls reset on intake-form."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        # Find the intake-clear handler
        clear_handler = js.split('intake-clear')[1].split("});")[0]
        assert "reset" in clear_handler

    def test_intake_clear_hides_decision(self):
        """Clear handler hides intake-decision panel."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        clear_handler = js.split('intake-clear')[1].split("});")[0]
        assert "intake-decision" in clear_handler
        assert "hidden" in clear_handler

    def test_source_filter_dropdown_options(self):
        """Source filter dropdown has all known sources."""
        with open("app/operator_ui/index.html") as f:
            html = f.read()
        source_section = html.split('id="opp-source-filter"')[1].split("</select>")[0]
        assert 'value="manual"' in source_section
        assert 'value="intake"' in source_section
        assert 'value="review_queue"' in source_section
        assert 'value="import"' in source_section

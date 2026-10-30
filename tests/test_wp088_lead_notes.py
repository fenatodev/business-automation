"""WP-088 — Lead notes UI and backend contract tests."""
import pytest


@pytest.fixture
def operator_ui():
    """Read the operator UI files."""
    import pathlib
    base = pathlib.Path("app/operator_ui")
    return {
        "html": (base / "index.html").read_text(),
        "js": (base / "app.js").read_text(),
        "css": (base / "styles.css").read_text(),
    }


class TestLeadNotesBackend:
    """Verify the lead notes backend changes."""

    def test_lead_update_schema_has_interest(self):
        """LeadUpdate schema includes interest field."""
        import pathlib
        code = (pathlib.Path("app/schemas.py")).read_text()
        lu_section = code[code.index("class LeadUpdate"):code.index("class LeadUpdate") + 500]
        assert "interest" in lu_section

    def test_lead_update_interest_is_optional(self):
        """LeadUpdate.interest is optional (str | None)."""
        import pathlib
        code = (pathlib.Path("app/schemas.py")).read_text()
        lu_section = code[code.index("class LeadUpdate"):code.index("class LeadUpdate") + 500]
        assert "interest: str | None" in lu_section

    def test_lead_update_status_is_optional(self):
        """LeadUpdate.status is optional so interest-only updates work."""
        import pathlib
        code = (pathlib.Path("app/schemas.py")).read_text()
        lu_section = code[code.index("class LeadUpdate"):code.index("class LeadUpdate") + 500]
        assert "| None = None" in lu_section

    def test_leads_router_updates_interest(self):
        """PATCH /leads/{lead_id} updates interest field."""
        import pathlib
        code = (pathlib.Path("app/routers/leads.py")).read_text()
        assert "lead.interest = data.interest" in code

    def test_leads_router_conditional_interest_update(self):
        """Interest is only updated when provided (not None)."""
        import pathlib
        code = (pathlib.Path("app/routers/leads.py")).read_text()
        assert "if data.interest is not None" in code


class TestLeadNotesJavaScript:
    """Verify the lead notes JavaScript functions."""

    def test_update_lead_notes_function(self, operator_ui):
        """updateLeadNotes function is defined."""
        assert "async function updateLeadNotes(" in operator_ui["js"]

    def test_update_lead_notes_sends_patch(self, operator_ui):
        """updateLeadNotes sends PATCH with interest body."""
        js = operator_ui["js"]
        # Find the function definition, not the call site
        func_def = js.index("async function updateLeadNotes(")
        notes_section = js[func_def:func_def + 800]
        assert '"PATCH"' in notes_section
        assert "interest" in notes_section

    def test_notes_textarea_in_render(self, operator_ui):
        """renderLeads creates notes textarea."""
        js = operator_ui["js"]
        assert 'className = "lead-notes"' in js or '.className = "lead-notes"' in js

    def test_notes_textarea_change_handler(self, operator_ui):
        """Notes textarea has change event listener."""
        js = operator_ui["js"]
        assert 'addEventListener("change"' in js
        assert "updateLeadNotes" in js

    def test_notes_textarea_shows_existing_interest(self, operator_ui):
        """Notes textarea pre-fills with lead.interest."""
        js = operator_ui["js"]
        assert "lead.interest" in js

    def test_wp088_comment_in_js(self, operator_ui):
        """JS contains WP-088 reference comment."""
        assert "WP-088" in operator_ui["js"]


class TestLeadNotesCSS:
    """Verify the lead notes CSS styles."""

    def test_lead_notes_style(self, operator_ui):
        """.lead-notes style exists."""
        assert ".lead-notes" in operator_ui["css"]

    def test_lead_notes_focus_style(self, operator_ui):
        """.lead-notes:focus style exists."""
        assert ".lead-notes:focus" in operator_ui["css"]

    def test_wp088_comment_in_css(self, operator_ui):
        """CSS contains WP-088 reference comment."""
        assert "WP-088" in operator_ui["css"]

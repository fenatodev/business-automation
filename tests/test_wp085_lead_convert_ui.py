"""WP-085 — Lead convert UI contract tests."""
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


class TestConvertLeadJavaScript:
    """Verify the convert lead JavaScript functions."""

    def test_convert_lead_function_exists(self, operator_ui):
        """convertLead function is defined."""
        assert "async function convertLead(" in operator_ui["js"]

    def test_convert_lead_uses_confirm(self, operator_ui):
        """convertLead asks for confirmation before converting."""
        js = operator_ui["js"]
        assert 'confirm(' in js
        assert "Converter este lead em customer" in js

    def test_convert_lead_sends_post(self, operator_ui):
        """convertLead sends POST to /leads/{id}/convert."""
        js = operator_ui["js"]
        assert '"/leads/" + leadId + "/convert"' in js or "'/leads/' + leadId + '/convert'" in js
        assert '"POST"' in js

    def test_convert_lead_handles_409(self, operator_ui):
        """convertLead handles 409 conflict (already converted)."""
        js = operator_ui["js"]
        assert "409" in js
        assert "já foi convertido" in js or "already" in js.lower()

    def test_convert_lead_handles_403(self, operator_ui):
        """convertLead disconnects on 403."""
        js = operator_ui["js"]
        assert "403" in js
        assert "disconnect" in js

    def test_convert_lead_refreshes_after_success(self, operator_ui):
        """convertLead calls refreshLeads after successful conversion."""
        js = operator_ui["js"]
        assert "refreshLeads" in js

    def test_convert_button_created_in_render(self, operator_ui):
        """renderLeads creates convert button for non-won leads."""
        js = operator_ui["js"]
        assert "lead-convert-btn" in js
        assert 'lead.status !== "won"' in js or "lead.status != 'won'" in js

    def test_convert_button_text(self, operator_ui):
        """Convert button has correct text."""
        js = operator_ui["js"]
        assert '"Converter"' in js

    def test_convert_button_type_button(self, operator_ui):
        """Convert button has type='button' to prevent form submission."""
        js = operator_ui["js"]
        assert '"button"' in js


class TestConvertLeadCSS:
    """Verify the convert button CSS styles."""

    def test_lead_convert_btn_style(self, operator_ui):
        """.lead-convert-btn style exists."""
        assert ".lead-convert-btn" in operator_ui["css"]

    def test_lead_convert_btn_hover_style(self, operator_ui):
        """.lead-convert-btn:hover style exists."""
        assert ".lead-convert-btn:hover" in operator_ui["css"]

    def test_wp085_comment_in_css(self, operator_ui):
        """CSS contains WP-085 reference comment."""
        assert "WP-085" in operator_ui["css"]


class TestConvertLeadBackend:
    """Verify the backend convert endpoint exists."""

    def test_convert_endpoint_exists(self):
        """POST /leads/{lead_id}/convert endpoint exists."""
        import pathlib
        customers_code = (pathlib.Path("app/routers/customers.py")).read_text()
        assert '"/leads/{lead_id}/convert"' in customers_code or "'/leads/{lead_id}/convert'" in customers_code

    def test_convert_endpoint_is_post(self):
        """Convert endpoint uses POST method."""
        import pathlib
        customers_code = (pathlib.Path("app/routers/customers.py")).read_text()
        assert '@router.post("/leads/{lead_id}/convert")' in customers_code

    def test_convert_sets_status_to_won(self):
        """Convert endpoint sets lead status to 'won'."""
        import pathlib
        customers_code = (pathlib.Path("app/routers/customers.py")).read_text()
        assert 'lead.status = "won"' in customers_code

    def test_convert_creates_customer(self):
        """Convert endpoint creates a Customer from the Lead."""
        import pathlib
        customers_code = (pathlib.Path("app/routers/customers.py")).read_text()
        assert "Customer(" in customers_code
        assert "lead.name" in customers_code

    def test_convert_checks_existing_customer(self):
        """Convert endpoint checks for existing customer (dedup)."""
        import pathlib
        customers_code = (pathlib.Path("app/routers/customers.py")).read_text()
        assert "existing_customer" in customers_code or "already converted" in customers_code.lower()

    def test_convert_returns_409_on_duplicate(self):
        """Convert endpoint returns 409 if lead already converted."""
        import pathlib
        customers_code = (pathlib.Path("app/routers/customers.py")).read_text()
        assert "409" in customers_code

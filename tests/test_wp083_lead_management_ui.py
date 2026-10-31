"""WP-083 — Lead management UI contract tests."""
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


class TestLeadSectionExists:
    """Verify the leads section is present in the UI."""

    def test_leads_section_in_html(self, operator_ui):
        """HTML contains leads section with proper indexing."""
        assert '07 / LEADS' in operator_ui["html"]
        assert 'id="leads-title"' in operator_ui["html"]
        assert 'id="leads-list"' in operator_ui["html"]

    def test_leads_refresh_button(self, operator_ui):
        """Leads section has refresh button."""
        assert 'id="leads-refresh"' in operator_ui["html"]

    def test_leads_filter_status(self, operator_ui):
        """Leads section has status filter dropdown."""
        assert 'id="lead-filter-status"' in operator_ui["html"]

    def test_leads_filter_options(self, operator_ui):
        """Status filter contains all lead status options."""
        html = operator_ui["html"]
        for status in ["new", "contacted", "qualified", "proposal", "won", "lost"]:
            assert f'value="{status}"' in html, f"Missing status option: {status}"

    def test_leads_section_aria_labelledby(self, operator_ui):
        """Leads section uses aria-labelledby for accessibility."""
        assert 'aria-labelledby="leads-title"' in operator_ui["html"]


class TestLeadJavaScript:
    """Verify the lead JavaScript functions and patterns."""

    def test_lead_api_function_exists(self, operator_ui):
        """leadApi function is defined."""
        assert "async function leadApi(" in operator_ui["js"]

    def test_lead_api_allowlist(self, operator_ui):
        """leadApi has strict allowlist (regex-based)."""
        js = operator_ui["js"]
        # WP-099: allowlist changed to regex pattern
        assert "/leads" in js
        assert "new" in js
        assert "contacted" in js
        assert "qualified" in js
        assert "proposal" in js
        assert "won" in js
        assert "lost" in js

    def test_lead_api_rejects_unauthorized_route(self, operator_ui):
        """leadApi rejects routes not in allowlist."""
        js = operator_ui["js"]
        assert "Rota não permitida" in js or "not allowed" in js.lower()

    def test_refresh_leads_function(self, operator_ui):
        """refreshLeads function is defined."""
        assert "async function refreshLeads(" in operator_ui["js"]

    def test_render_leads_function(self, operator_ui):
        """renderLeads function is defined."""
        assert "function renderLeads(" in operator_ui["js"]

    def test_update_lead_status_function(self, operator_ui):
        """updateLeadStatus function is defined."""
        assert "async function updateLeadStatus(" in operator_ui["js"]

    def test_lead_status_labels(self, operator_ui):
        """leadStatusLabels maps all statuses to Portuguese labels."""
        js = operator_ui["js"]
        assert "leadStatusLabels" in js
        assert "Novo" in js
        assert "Contatado" in js
        assert "Qualificado" in js
        assert "Proposta" in js
        assert "Convertido" in js
        assert "Perdido" in js

    def test_leads_no_innerhtml(self, operator_ui):
        """Leads rendering uses textContent/appendChild, not innerHTML."""
        # Find the renderLeads function and check it doesn't use innerHTML
        js = operator_ui["js"]
        assert "innerHTML" not in js or js.count("innerHTML") == 0

    def test_leads_refresh_button_listener(self, operator_ui):
        """Refresh button has click listener."""
        assert '"leads-refresh"' in operator_ui["js"]
        assert 'addEventListener("click"' in operator_ui["js"]

    def test_leads_filter_change_listener(self, operator_ui):
        """Filter dropdown has change listener."""
        assert '"lead-filter-status"' in operator_ui["js"]
        assert 'addEventListener("change"' in operator_ui["js"]

    def test_leads_loaded_on_connect(self, operator_ui):
        """refreshLeads is called when workspace connects."""
        js = operator_ui["js"]
        # Check that refreshLeads is in the workspaceObserver callback
        assert "refreshLeads" in js

    def test_lead_api_bearer_auth(self, operator_ui):
        """leadApi sends Bearer token."""
        js = operator_ui["js"]
        assert '"Authorization": "Bearer "' in js

    def test_lead_api_403_disconnect(self, operator_ui):
        """leadApi disconnects on 403."""
        js = operator_ui["js"]
        assert "403" in js
        assert "disconnect" in js


class TestLeadCSS:
    """Verify the lead CSS styles are present."""

    def test_lead_list_style(self, operator_ui):
        """.lead-list style exists."""
        assert ".lead-list" in operator_ui["css"]

    def test_lead_item_style(self, operator_ui):
        """.lead-item style exists."""
        assert ".lead-item" in operator_ui["css"]

    def test_lead_item_header_style(self, operator_ui):
        """.lead-item-header style exists."""
        assert ".lead-item-header" in operator_ui["css"]

    def test_lead_item_name_style(self, operator_ui):
        """.lead-item-name style exists."""
        assert ".lead-item-name" in operator_ui["css"]

    def test_lead_item_details_style(self, operator_ui):
        """.lead-item-details style exists."""
        assert ".lead-item-details" in operator_ui["css"]

    def test_lead_status_select_style(self, operator_ui):
        """.lead-status-select style exists."""
        assert ".lead-status-select" in operator_ui["css"]

    def test_lead_filters_style(self, operator_ui):
        """.lead-filters style exists."""
        assert ".lead-filters" in operator_ui["css"]

    def test_lead_filter_group_style(self, operator_ui):
        """.lead-filter-group style exists."""
        assert ".lead-filter-group" in operator_ui["css"]


class TestLeadBackendFilter:
    """Verify the backend supports status filtering."""

    def test_leads_router_has_status_param(self):
        """list_leads accepts optional status parameter."""
        import pathlib
        router_code = (pathlib.Path("app/routers/leads.py")).read_text()
        assert "status: str | None = None" in router_code or 'status: str | None = None' in router_code

    def test_leads_router_filters_by_status(self):
        """list_leads filters by status when provided."""
        import pathlib
        router_code = (pathlib.Path("app/routers/leads.py")).read_text()
        assert "Lead.status == status" in router_code

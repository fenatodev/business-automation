"""WP-086 — Customer list UI contract tests."""
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


class TestCustomerSectionExists:
    """Verify the customers section is present in the UI."""

    def test_customers_section_in_html(self, operator_ui):
        """HTML contains customers section with proper indexing."""
        assert "08 / CUSTOMERS" in operator_ui["html"]
        assert 'id="customers-title"' in operator_ui["html"]
        assert 'id="customers-list"' in operator_ui["html"]

    def test_customers_refresh_button(self, operator_ui):
        """Customers section has refresh button."""
        assert 'id="customers-refresh"' in operator_ui["html"]

    def test_customers_section_aria_labelledby(self, operator_ui):
        """Customers section uses aria-labelledby for accessibility."""
        assert 'aria-labelledby="customers-title"' in operator_ui["html"]


class TestCustomerJavaScript:
    """Verify the customer JavaScript functions and patterns."""

    def test_customer_api_function_exists(self, operator_ui):
        """customerApi function is defined."""
        assert "async function customerApi(" in operator_ui["js"]

    def test_customer_api_allowlist(self, operator_ui):
        """customerApi has strict allowlist."""
        js = operator_ui["js"]
        assert '"/customers"' in js

    def test_customer_api_rejects_unauthorized_route(self, operator_ui):
        """customerApi rejects routes not in allowlist."""
        js = operator_ui["js"]
        assert "Rota não permitida" in js or "not allowed" in js.lower()

    def test_refresh_customers_function(self, operator_ui):
        """refreshCustomers function is defined."""
        assert "async function refreshCustomers(" in operator_ui["js"]

    def test_render_customers_function(self, operator_ui):
        """renderCustomers function is defined."""
        assert "function renderCustomers(" in operator_ui["js"]

    def test_customers_no_innerhtml(self, operator_ui):
        """Customers rendering uses textContent/appendChild, not innerHTML."""
        js = operator_ui["js"]
        assert "innerHTML" not in js or js.count("innerHTML") == 0

    def test_customers_refresh_button_listener(self, operator_ui):
        """Refresh button has click listener."""
        assert '"customers-refresh"' in operator_ui["js"]
        assert 'addEventListener("click"' in operator_ui["js"]

    def test_customers_loaded_on_connect(self, operator_ui):
        """refreshCustomers is called when workspace connects."""
        js = operator_ui["js"]
        assert "refreshCustomers" in js

    def test_customer_api_bearer_auth(self, operator_ui):
        """customerApi sends Bearer token."""
        js = operator_ui["js"]
        assert '"Authorization": "Bearer "' in js

    def test_customer_api_403_disconnect(self, operator_ui):
        """customerApi disconnects on 403."""
        js = operator_ui["js"]
        assert "403" in js
        assert "disconnect" in js

    def test_render_customers_shows_phone(self, operator_ui):
        """renderCustomers displays phone when present."""
        js = operator_ui["js"]
        assert "cust.phone" in js

    def test_render_customers_shows_email(self, operator_ui):
        """renderCustomers displays email when present."""
        js = operator_ui["js"]
        assert "cust.email" in js

    def test_render_customers_shows_lead_id(self, operator_ui):
        """renderCustomers displays lead_id when present."""
        js = operator_ui["js"]
        assert "cust.lead_id" in js

    def test_render_customers_empty_state(self, operator_ui):
        """renderCustomers shows empty state message."""
        js = operator_ui["js"]
        assert "Nenhum customer encontrado" in js


class TestCustomerCSS:
    """Verify the customer CSS styles are present."""

    def test_customer_list_style(self, operator_ui):
        """.customer-list style exists."""
        assert ".customer-list" in operator_ui["css"]

    def test_customer_item_style(self, operator_ui):
        """.customer-item style exists."""
        assert ".customer-item" in operator_ui["css"]

    def test_customer_item_header_style(self, operator_ui):
        """.customer-item-header style exists."""
        assert ".customer-item-header" in operator_ui["css"]

    def test_customer_item_name_style(self, operator_ui):
        """.customer-item-name style exists."""
        assert ".customer-item-name" in operator_ui["css"]

    def test_customer_item_details_style(self, operator_ui):
        """.customer-item-details style exists."""
        assert ".customer-item-details" in operator_ui["css"]

    def test_wp086_comment_in_css(self, operator_ui):
        """CSS contains WP-086 reference comment."""
        assert "WP-086" in operator_ui["css"]


class TestCustomerBackend:
    """Verify the backend customer endpoint exists."""

    def test_list_customers_endpoint_exists(self):
        """GET /customers endpoint exists."""
        import pathlib
        customers_code = (pathlib.Path("app/routers/customers.py")).read_text()
        assert '"/customers"' in customers_code

    def test_list_customers_is_get(self):
        """List customers endpoint uses GET method."""
        import pathlib
        customers_code = (pathlib.Path("app/routers/customers.py")).read_text()
        assert '@router.get("/customers")' in customers_code

    def test_list_customers_filters_by_company(self):
        """List customers filters by tenant company_id."""
        import pathlib
        customers_code = (pathlib.Path("app/routers/customers.py")).read_text()
        assert "company_id" in customers_code

"""WP-087 — Customer_id filter in conversations backend tests."""
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


class TestConversationCustomerFilterBackend:
    """Verify the customer_id filter is present in conversations backend."""

    def test_list_conversations_accepts_customer_id_param(self):
        """list_company_conversations has customer_id query param."""
        import pathlib
        code = (pathlib.Path("app/routers/conversations.py")).read_text()
        assert "customer_id: int | None = Query(None" in code

    def test_list_conversations_filters_by_customer_id(self):
        """list_company_conversations filters by Conversation.customer_id."""
        import pathlib
        code = (pathlib.Path("app/routers/conversations.py")).read_text()
        assert "Conversation.customer_id == customer_id" in code

    def test_count_conversations_accepts_customer_id_param(self):
        """count_company_conversations has customer_id query param."""
        import pathlib
        code = (pathlib.Path("app/routers/conversations.py")).read_text()
        # The count endpoint should also have customer_id
        count_section = code[code.index('"/companies/{company_id}/conversations/count"'):code.index('"/companies/{company_id}/conversations/count"') + 1500]
        assert "customer_id" in count_section

    def test_count_conversations_filters_by_customer_id(self):
        """count_company_conversations filters by Conversation.customer_id."""
        import pathlib
        code = (pathlib.Path("app/routers/conversations.py")).read_text()
        # Count endpoint should also filter by customer_id
        count_section = code[code.index('"/companies/{company_id}/conversations/count"'):code.index('"/companies/{company_id}/conversations/count"') + 1500]
        assert "Conversation.customer_id == customer_id" in count_section


class TestCustomerDetailHTML:
    """Verify the customer detail section is present in HTML."""

    def test_customer_detail_section_exists(self, operator_ui):
        """HTML contains customer detail section."""
        assert 'id="customer-detail"' in operator_ui["html"]

    def test_customer_detail_hidden_by_default(self, operator_ui):
        """Customer detail is hidden by default."""
        assert 'id="customer-detail" class="customer-detail" hidden' in operator_ui["html"]

    def test_customer_detail_back_button(self, operator_ui):
        """Customer detail has back button."""
        assert 'id="customer-detail-back"' in operator_ui["html"]

    def test_customer_detail_name_header(self, operator_ui):
        """Customer detail has name header."""
        assert 'id="customer-detail-name"' in operator_ui["html"]

    def test_customer_detail_info_section(self, operator_ui):
        """Customer detail has info section."""
        assert 'id="customer-detail-info"' in operator_ui["html"]

    def test_customer_conversations_list(self, operator_ui):
        """Customer detail has conversations list container."""
        assert 'id="customer-conversations-list"' in operator_ui["html"]


class TestCustomerDetailJavaScript:
    """Verify the customer detail JavaScript functions."""

    def test_show_customer_detail_function(self, operator_ui):
        """showCustomerDetail function is defined."""
        assert "async function showCustomerDetail(" in operator_ui["js"]

    def test_hide_customer_detail_function(self, operator_ui):
        """hideCustomerDetail function is defined."""
        assert "function hideCustomerDetail(" in operator_ui["js"]

    def test_load_customer_conversations_function(self, operator_ui):
        """loadCustomerConversations function is defined."""
        assert "async function loadCustomerConversations(" in operator_ui["js"]

    def test_customer_item_click_handler(self, operator_ui):
        """Customer items have click handler to show detail."""
        js = operator_ui["js"]
        assert 'addEventListener("click"' in js
        assert "showCustomerDetail" in js

    def test_customer_detail_back_button_handler(self, operator_ui):
        """Back button calls hideCustomerDetail."""
        js = operator_ui["js"]
        assert '"customer-detail-back"' in js
        assert "hideCustomerDetail" in js

    def test_load_customer_conversations_uses_customer_id_filter(self, operator_ui):
        """loadCustomerConversations builds URL with customer_id param."""
        js = operator_ui["js"]
        assert "customer_id" in js
        assert "URLSearchParams" in js or "customer_id=" in js

    def test_customer_detail_uses_text_content(self, operator_ui):
        """Customer detail rendering uses textContent, not innerHTML."""
        js = operator_ui["js"]
        # The customer detail section should use textContent
        detail_section = js[js.index("showCustomerDetail"):js.index("showCustomerDetail") + 1500]
        assert "textContent" in detail_section

    def test_customer_detail_toggles_hidden(self, operator_ui):
        """showCustomerDetail toggles hidden attribute."""
        js = operator_ui["js"]
        assert 'customers-list").hidden' in js
        assert 'customer-detail").hidden' in js

    def test_current_customer_id_state(self, operator_ui):
        """currentCustomerId state variable exists."""
        assert "currentCustomerId" in operator_ui["js"]


class TestCustomerDetailCSS:
    """Verify the customer detail CSS styles."""

    def test_customer_detail_style(self, operator_ui):
        """.customer-detail style exists."""
        assert ".customer-detail" in operator_ui["css"]

    def test_customer_detail_header_style(self, operator_ui):
        """.customer-detail-header style exists."""
        assert ".customer-detail-header" in operator_ui["css"]

    def test_customer_detail_info_style(self, operator_ui):
        """.customer-detail-info style exists."""
        assert ".customer-detail-info" in operator_ui["css"]

    def test_customer_conv_list_style(self, operator_ui):
        """.customer-conv-list style exists."""
        assert ".customer-conv-list" in operator_ui["css"]

    def test_customer_conv_item_style(self, operator_ui):
        """.customer-conv-item style exists."""
        assert ".customer-conv-item" in operator_ui["css"]

    def test_customer_conv_header_style(self, operator_ui):
        """.customer-conv-header style exists."""
        assert ".customer-conv-header" in operator_ui["css"]

    def test_wp087_comment_in_css(self, operator_ui):
        """CSS contains WP-087 reference comment."""
        assert "WP-087" in operator_ui["css"]

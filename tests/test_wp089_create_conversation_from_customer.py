"""WP-089 — Create conversation from customer UI contract tests."""
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


class TestCreateConversationHTML:
    """Verify the new conversation button is present."""

    def test_new_conv_button_exists(self, operator_ui):
        """HTML contains new conversation button."""
        assert 'id="customer-new-conv"' in operator_ui["html"]

    def test_new_conv_button_text(self, operator_ui):
        """New conversation button has correct text."""
        assert "Nova conversa" in operator_ui["html"]


class TestCreateConversationJavaScript:
    """Verify the create conversation JavaScript functions."""

    def test_create_conversation_function(self, operator_ui):
        """createConversationFromCustomer function is defined."""
        assert "async function createConversationFromCustomer(" in operator_ui["js"]

    def test_create_conversation_uses_prompt(self, operator_ui):
        """createConversationFromCustomer asks for channel via prompt."""
        js = operator_ui["js"]
        func = js[js.index("createConversationFromCustomer("):js.index("createConversationFromCustomer(") + 1200]
        assert "prompt(" in func

    def test_create_conversation_validates_channel(self, operator_ui):
        """createConversationFromCustomer validates channel against allowlist."""
        js = operator_ui["js"]
        func = js[js.index("createConversationFromCustomer("):js.index("createConversationFromCustomer(") + 1200]
        assert "allowedChannels" in func or "whatsapp" in func

    def test_create_conversation_sends_post(self, operator_ui):
        """createConversationFromCustomer sends POST to /conversations."""
        js = operator_ui["js"]
        func = js[js.index("createConversationFromCustomer("):js.index("createConversationFromCustomer(") + 1200]
        assert '"/conversations"' in func
        assert '"POST"' in func

    def test_create_conversation_includes_customer_id(self, operator_ui):
        """createConversationFromCustomer includes customer_id in body."""
        js = operator_ui["js"]
        func = js[js.index("createConversationFromCustomer("):js.index("createConversationFromCustomer(") + 1200]
        assert "customer_id" in func

    def test_create_conversation_handles_403(self, operator_ui):
        """createConversationFromCustomer handles 403."""
        js = operator_ui["js"]
        func = js[js.index("createConversationFromCustomer("):js.index("createConversationFromCustomer(") + 1200]
        assert "403" in func

    def test_create_conversation_refreshes_list(self, operator_ui):
        """createConversationFromCustomer reloads conversations after success."""
        js = operator_ui["js"]
        func_def = js.index("async function createConversationFromCustomer(")
        func = js[func_def:func_def + 2000]
        assert "loadCustomerConversations" in func

    def test_new_conv_button_handler(self, operator_ui):
        """New conversation button has click handler."""
        js = operator_ui["js"]
        assert '"customer-new-conv"' in js
        assert "createConversationFromCustomer" in js

    def test_wp089_comment_in_js(self, operator_ui):
        """JS contains WP-089 reference comment."""
        assert "WP-089" in operator_ui["js"]


class TestCreateConversationBackend:
    """Verify the backend conversation creation supports customer_id."""

    def test_conversation_create_accepts_customer_id(self):
        """ConversationCreate schema has customer_id field."""
        import pathlib
        code = (pathlib.Path("app/schemas.py")).read_text()
        cc_section = code[code.index("class ConversationCreate"):code.index("class ConversationCreate") + 500]
        assert "customer_id" in cc_section

    def test_create_conversation_endpoint_exists(self):
        """POST /conversations endpoint exists."""
        import pathlib
        code = (pathlib.Path("app/routers/conversations.py")).read_text()
        assert '@router.post("/conversations")' in code

    def test_create_conversation_validates_customer_id_or_lead_id(self):
        """Create conversation requires lead_id or customer_id."""
        import pathlib
        code = (pathlib.Path("app/routers/conversations.py")).read_text()
        assert "lead_id is None and data.customer_id is None" in code

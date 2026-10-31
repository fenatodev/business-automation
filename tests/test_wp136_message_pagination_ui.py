"""WP-136 — Message pagination UI contract tests.

Verifies that conversation messages are loaded with pagination (limit/offset)
instead of loading all messages at once.
"""

import pytest


class TestMessagePaginationUI:
    """Verify message pagination is properly connected in the operator UI."""

    def _get_app_js(self):
        with open("app/operator_ui/app.js") as f:
            return f.read()

    def _get_index_html(self):
        with open("app/operator_ui/index.html") as f:
            return f.read()

    # --- State variables ---

    def test_msg_offset_state_variable(self):
        """app.js should have msgOffset state variable."""
        js = self._get_app_js()
        assert "msgOffset" in js

    def test_msg_page_size_constant(self):
        """app.js should have msgPageSize constant."""
        js = self._get_app_js()
        assert "msgPageSize" in js

    def test_msg_total_state_variable(self):
        """app.js should have msgTotal state variable."""
        js = self._get_app_js()
        assert "msgTotal" in js

    # --- loadMessages function ---

    def test_load_messages_function_exists(self):
        """app.js should have loadMessages function."""
        js = self._get_app_js()
        assert "function loadMessages(" in js or "async function loadMessages(" in js

    def test_load_messages_uses_pagination_params(self):
        """loadMessages should include limit and offset in the API call."""
        js = self._get_app_js()
        assert "msgPageSize" in js
        assert "msgOffset" in js
        # Verify the messages endpoint is called with query params
        assert "/messages?limit=" in js or '"/messages?limit=' in js

    def test_load_messages_calls_count_endpoint(self):
        """loadMessages should call the count endpoint for pagination."""
        js = self._get_app_js()
        assert "/messages/count" in js

    # --- selectConversation resets msgOffset ---

    def test_select_conversation_resets_msg_offset(self):
        """selectConversation should reset msgOffset to 0."""
        js = self._get_app_js()
        # Find selectConversation function
        start = js.find("async function selectConversation(")
        if start == -1:
            start = js.find("function selectConversation(")
        assert start != -1, "selectConversation function not found"
        end = js.find("\n}", start + 200)
        func_body = js[start:end] if end != -1 else js[start:start+500]
        assert "msgOffset = 0" in func_body, (
            "selectConversation should reset msgOffset to 0"
        )

    # --- updateMessagePagination function ---

    def test_update_message_pagination_function_exists(self):
        """app.js should have updateMessagePagination function."""
        js = self._get_app_js()
        assert "updateMessagePagination" in js

    # --- HTML elements ---

    def test_msg_pagination_container_exists(self):
        """HTML should have msg-pagination container."""
        html = self._get_index_html()
        assert 'id="msg-pagination"' in html

    def test_msg_prev_button_exists(self):
        """HTML should have msg-prev button."""
        html = self._get_index_html()
        assert 'id="msg-prev"' in html

    def test_msg_next_button_exists(self):
        """HTML should have msg-next button."""
        html = self._get_index_html()
        assert 'id="msg-next"' in html

    def test_msg_page_span_exists(self):
        """HTML should have msg-page span."""
        html = self._get_index_html()
        assert 'id="msg-page"' in html

    def test_msg_pagination_inside_conv_detail(self):
        """msg-pagination should be inside conv-detail."""
        html = self._get_index_html()
        detail_pos = html.find('id="conv-detail"')
        msg_pag_pos = html.find('id="msg-pagination"')
        form_pos = html.find('id="human-reply-form"')
        assert detail_pos != -1 and msg_pag_pos != -1
        assert msg_pag_pos > detail_pos, "msg-pagination should be inside conv-detail"
        assert msg_pag_pos < form_pos, "msg-pagination should be before reply form"

    # --- Event listeners ---

    def test_msg_prev_listener_exists(self):
        """msg-prev should have a click listener."""
        js = self._get_app_js()
        assert 'msg-prev' in js

    def test_msg_next_listener_exists(self):
        """msg-next should have a click listener."""
        js = self._get_app_js()
        assert 'msg-next' in js

    # --- Allowlist ---

    def test_conversation_api_allows_messages_count(self):
        """conversationApi allowlist should allow /messages/count."""
        js = self._get_app_js()
        assert r'messages(/count)?' in js or 'messages(\/count)?' in js

    # --- Disconnect cleanup ---

    def test_disconnect_resets_msg_offset(self):
        """disconnect should reset msgOffset and msgTotal."""
        js = self._get_app_js()
        # Find disconnect function
        start = js.find("function disconnect(")
        assert start != -1, "disconnect function not found"
        end = js.find("\n}", start + 500)
        func_body = js[start:end] if end != -1 else js[start:start+800]
        assert "msgOffset = 0" in func_body, "disconnect should reset msgOffset"
        assert "msgTotal = 0" in func_body, "disconnect should reset msgTotal"

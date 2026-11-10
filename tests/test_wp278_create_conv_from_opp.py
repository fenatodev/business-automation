"""WP-278: Test create conversation from opportunity in operator UI."""

import os

UI_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "operator_ui")
HTML = open(os.path.join(UI_DIR, "index.html"), encoding="utf-8").read()
JS = open(os.path.join(UI_DIR, "app.js"), encoding="utf-8").read()
CSS = open(os.path.join(UI_DIR, "styles.css"), encoding="utf-8").read()


class TestCreateConversationFromOpportunity:
    """Verify create conversation from opportunity implementation."""

    def test_html_has_create_conv_button(self):
        """HTML has create conversation button."""
        assert 'id="opp-create-conv"' in HTML

    def test_html_has_conv_form(self):
        """HTML has conversation form."""
        assert 'id="opp-conv-form"' in HTML

    def test_html_has_channel_select(self):
        """HTML has channel select."""
        assert 'id="opp-conv-channel"' in HTML

    def test_html_has_message_textarea(self):
        """HTML has message textarea."""
        assert 'id="opp-conv-message"' in HTML

    def test_html_has_suggest_button(self):
        """HTML has suggest button."""
        assert 'id="opp-conv-suggest"' in HTML

    def test_html_has_submit_button(self):
        """HTML has submit button."""
        assert 'id="opp-conv-submit"' in HTML

    def test_html_has_cancel_button(self):
        """HTML has cancel button."""
        assert 'id="opp-conv-cancel"' in HTML

    def test_html_has_suggestion_panel(self):
        """HTML has suggestion panel."""
        assert 'id="opp-conv-suggestion"' in HTML

    def test_js_has_create_conv_handler(self):
        """JS has handler for create conversation button."""
        assert 'opp-create-conv' in JS
        assert 'addEventListener("click"' in JS

    def test_js_has_suggest_handler(self):
        """JS has handler for suggest button."""
        assert 'opp-conv-suggest' in JS

    def test_js_has_submit_handler(self):
        """JS has handler for submit button."""
        assert 'opp-conv-submit' in JS

    def test_js_has_cancel_handler(self):
        """JS has handler for cancel button."""
        assert 'opp-conv-cancel' in JS

    def test_js_calls_conversationApi(self):
        """JS uses conversationApi to create conversation."""
        assert 'conversationApi("/conversations/", "POST"' in JS

    def test_js_sends_channel_and_company(self):
        """JS sends channel and company_id when creating conversation."""
        assert 'channel' in JS
        assert 'company_id' in JS

    def test_js_has_suggestion_state(self):
        """JS has oppConvSuggestion state variable."""
        assert 'oppConvSuggestion' in JS

    def test_js_allowlist_includes_suggest_message(self):
        """Allowlist includes /conversations/suggest-message."""
        assert '/conversations/suggest-message' in JS

    def test_css_has_conv_opp_form_styles(self):
        """CSS has styles for conv-opp-form."""
        assert ".conv-opp-form" in CSS

    def test_form_is_in_opp_conv_section(self):
        """Form is in the opportunity conversations section."""
        idx_section = HTML.index('id="opp-conv-section"')
        idx_form = HTML.index('id="opp-conv-form"')
        assert idx_section < idx_form

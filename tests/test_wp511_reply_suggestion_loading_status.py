"""WP-511 — Feedback durante sugestão automática de resposta.

Tests that the auto-suggestion loading status element exists in the HTML
and that the JavaScript sets "Gerando sugestão..." before the API call.
"""


class TestReplySuggestionLoadingStatus:
    """Test WP-511 loading status contract."""

    @classmethod
    def setup_class(cls):
        with open("app/operator_ui/index.html") as f:
            cls.html = f.read()
        with open("app/operator_ui/app.js") as f:
            cls.js = f.read()

    def test_auto_suggestion_status_element_exists(self):
        """The reply form has an auto-suggestion status element."""
        assert 'id="reply-auto-suggestion-status"' in self.html

    def test_auto_suggestion_status_has_role_status(self):
        """The status element is accessible with role=status."""
        import re
        match = re.search(r'id="reply-auto-suggestion-status"[^>]*', self.html)
        assert match is not None
        assert 'role="status"' in match.group(0)

    def test_auto_suggestion_status_has_aria_live(self):
        """The status element uses aria-live for screen readers."""
        import re
        match = re.search(r'id="reply-auto-suggestion-status"[^>]*', self.html)
        assert match is not None
        assert 'aria-live="polite"' in match.group(0)

    def test_js_sets_loading_text_before_fetch(self):
        """JS sets loading text before the suggest-reply fetch call."""
        # The loading text must appear before the fetch in the auto-suggest handler
        loading_pos = self.js.index('Gerando sugestão...')
        # Find the suggest-reply fetch that belongs to the auto-suggest handler
        # (WP-252 handler, not WP-226 manual button)
        toggle_pos = self.js.index('conv-reply-toggle')
        suggest_reply_pos = self.js.index('/suggest-reply', toggle_pos)
        assert loading_pos < suggest_reply_pos, (
            "Loading text should be set before the fetch call"
        )

    def test_js_clears_status_on_success(self):
        """JS clears the suggestion status when suggestion is applied."""
        # After setting reply-message value, status should be cleared
        set_value_pos = self.js.index('reply-message").value = data.suggestion')
        clear_status_pos = self.js.index(
            'suggestionStatus.textContent = ""', set_value_pos
        )
        assert clear_status_pos > set_value_pos

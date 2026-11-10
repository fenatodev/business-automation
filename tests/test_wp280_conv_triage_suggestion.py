"""WP-280 — AI triage suggestion for conversations UI contract tests."""
import pytest

JS_PATH = "app/operator_ui/app.js"
HTML_PATH = "app/operator_ui/index.html"


@pytest.fixture
def js():
    with open(JS_PATH) as f:
        return f.read()


@pytest.fixture
def html():
    with open(HTML_PATH) as f:
        return f.read()


class TestTriageSuggestionButton:
    def test_button_exists_in_html(self, html):
        assert 'id="conv-suggest-triage"' in html

    def test_button_label(self, html):
        assert "🤖 Sugerir triagem" in html

    def test_button_in_conv_detail_actions(self, html):
        idx_actions = html.index("conv-detail-actions")
        idx_button = html.index("conv-suggest-triage", idx_actions)
        assert idx_button > idx_actions

    def test_panel_exists_in_html(self, html):
        assert 'id="conv-triage-suggestion"' in html
        assert 'id="conv-triage-suggestion-content"' in html

    def test_apply_button_exists(self, html):
        assert 'id="apply-conv-triage-suggestion"' in html

    def test_dismiss_button_exists(self, html):
        assert 'id="dismiss-conv-triage-suggestion"' in html


class TestTriageSuggestionJS:
    def test_click_handler_exists(self, js):
        assert 'conv-suggest-triage' in js
        assert "addEventListener" in js

    def test_calls_suggest_triage_endpoint(self, js):
        assert '"/conversations/" + convId + "/suggest-triage"' in js

    def test_uses_post_method(self, js):
        idx_triage = js.index('"/conversations/" + convId + "/suggest-triage"')
        section = js[idx_triage - 100 : idx_triage + 100]
        assert '"POST"' in section

    def test_handles_503_error(self, js):
        idx_triage = js.index("conv-suggest-triage")
        idx_next = js.index("WP-280", idx_triage + 10) if "WP-280" in js[idx_triage + 10:] else idx_triage + 2000
        section = js[idx_triage:idx_next]
        assert "503" in section

    def test_shows_loading_state(self, js):
        assert "Analisando" in js

    def test_restores_button_text(self, js):
        assert "🤖 Sugerir triagem" in js

    def test_render_function_exists(self, js):
        assert "renderConvTriageSuggestion" in js

    def test_render_shows_next_action(self, js):
        assert "next_action" in js

    def test_render_shows_confidence(self, js):
        assert "confidence" in js

    def test_render_shows_reason(self, js):
        assert "reason" in js

    def test_apply_handler_exists(self, js):
        assert "apply-conv-triage-suggestion" in js

    def test_dismiss_handler_exists(self, js):
        assert "dismiss-conv-triage-suggestion" in js

    def test_state_variable_exists(self, js):
        assert "convTriageSuggestion" in js

    def test_shows_panel_on_success(self, js):
        assert 'conv-triage-suggestion' in js
        idx_panel = js.index("conv-triage-suggestion")
        idx_hidden = js.rindex("hidden", 0, idx_panel + 200)
        assert idx_hidden > 0


class TestAllowlist:
    def test_suggest_triage_in_allowlist(self, js):
        idx_api = js.index("async function conversationApi")
        idx_triage = js.index("/suggest-triage", idx_api)
        assert idx_triage - idx_api < 1500

    def test_suggest_triage_pattern_correct(self, js):
        assert "/suggest-triage" in js


class TestSelectConversation:
    def test_shows_triage_button_on_select(self, js):
        idx_select = js.index("async function selectConversation")
        idx_triage = js.index("conv-suggest-triage", idx_select)
        # Should be within selectConversation
        assert idx_triage - idx_select < 1500

    def test_hides_triage_panel_on_select(self, js):
        idx_select = js.index("async function selectConversation")
        idx_panel = js.index("conv-triage-suggestion", idx_select)
        assert idx_panel - idx_select < 1500

"""WP-279 — Conversation favorites UI contract tests."""
import pytest

JS_PATH = "app/operator_ui/app.js"
HTML_PATH = "app/operator_ui/index.html"
CSS_PATH = "app/operator_ui/styles.css"


@pytest.fixture
def js():
    with open(JS_PATH) as f:
        return f.read()


@pytest.fixture
def html():
    with open(HTML_PATH) as f:
        return f.read()


@pytest.fixture
def css():
    with open(CSS_PATH) as f:
        return f.read()


class TestFavoritesState:
    def test_conv_favorites_map_exists(self, js):
        assert "convFavorites" in js
        assert "new Map()" in js

    def test_toggle_function_exists(self, js):
        assert "toggleConversationFavorite" in js

    def test_toggle_calls_conversationApi(self, js):
        assert '"/conversations/" + id + "/favorite"' in js
        assert 'favorited:' in js

    def test_toggle_updates_map(self, js):
        assert "convFavorites.set" in js

    def test_toggle_refreshes_list(self, js):
        # After toggling, showConversationList should be called
        idx_toggle = js.index("toggleConversationFavorite")
        idx_list = js.index("showConversationList", idx_toggle)
        assert idx_list > idx_toggle

    def test_toggle_handles_error(self, js):
        idx_toggle = js.index("toggleConversationFavorite")
        section = js[idx_toggle : idx_toggle + 500]
        assert "ApiFailure" in section or "catch" in section


class TestFavoritesButton:
    def test_fav_button_created_in_list(self, js):
        assert "conv-fav-btn" in js

    def test_fav_button_has_aria_label(self, js):
        assert "Favoritar conversa" in js

    def test_fav_button_shows_star(self, js):
        # Should show filled star for favorites, empty for non-favorites
        assert "★" in js
        assert "☆" in js

    def test_fav_button_stops_propagation(self, js):
        assert "stopPropagation" in js

    def test_fav_button_triggers_toggle(self, js):
        # The click handler should call toggleConversationFavorite
        idx_fav = js.index("conv-fav-btn")
        idx_toggle = js.index("toggleConversationFavorite", idx_fav)
        assert idx_toggle > idx_fav


class TestAllowlist:
    def test_favorite_route_allowed(self, js):
        assert '"/conversations/\\d+/favorite"' in js or "/favorite" in js

    def test_favorite_in_conversationApi(self, js):
        idx_api = js.index("async function conversationApi")
        idx_favorite = js.index("/favorite", idx_api)
        # Should be within the allowlist section
        assert idx_favorite - idx_api < 1000


class TestCSS:
    def test_fav_button_style_exists(self, css):
        assert ".conv-fav-btn" in css

    def test_fav_button_has_cursor_pointer(self, css):
        idx = css.index(".conv-fav-btn")
        section = css[idx : idx + 300]
        assert "cursor: pointer" in section

    def test_fav_button_hover_exists(self, css):
        assert ".conv-fav-btn:hover" in css

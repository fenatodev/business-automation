"""WP-091 — Pending badge UI contract tests."""
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


class TestPendingBadgeHTML:
    def test_pending_badge_element_exists(self, operator_ui):
        assert 'id="pending-badge"' in operator_ui["html"]

    def test_pending_badge_hidden_by_default(self, operator_ui):
        assert 'class="pending-badge" hidden' in operator_ui["html"]

    def test_pending_badge_inside_list_title(self, operator_ui):
        html = operator_ui["html"]
        title_idx = html.index('id="list-title"')
        badge_idx = html.index('id="pending-badge"')
        assert title_idx < badge_idx


class TestPendingBadgeJavaScript:
    def test_pending_badge_in_refresh_list(self, operator_ui):
        js = operator_ui["js"]
        assert "pending-badge" in js

    def test_pending_count_filter(self, operator_ui):
        js = operator_ui["js"]
        assert 'next_action === "pending"' in js

    def test_pending_badge_text_content(self, operator_ui):
        js = operator_ui["js"]
        assert 'badge.textContent' in js

    def test_pending_badge_hidden_toggle(self, operator_ui):
        js = operator_ui["js"]
        assert 'badge.hidden' in js

    def test_wp091_comment(self, operator_ui):
        assert "WP-091" in operator_ui["js"]


class TestPendingBadgeCSS:
    def test_pending_badge_style(self, operator_ui):
        assert ".pending-badge" in operator_ui["css"]

    def test_pending_badge_has_background(self, operator_ui):
        css = operator_ui["css"]
        section = css[css.index(".pending-badge"):css.index(".pending-badge") + 300]
        assert "background" in section

    def test_wp091_comment_css(self, operator_ui):
        assert "WP-091" in operator_ui["css"]

"""WP-193 — Clickable next actions in dashboard.

Tests that the dashboard next actions are clickable and scroll to
the relevant section, improving the operator's workflow.
"""


class TestClickableNextActions:
    """Test next actions are clickable in JavaScript."""

    def test_next_action_click_handler_exists(self):
        """Next action items have click handlers."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        assert "next-action-item" in js
        # The click handler is in the full file
        assert "addEventListener" in js and "click" in js

    def test_next_action_cursor_pointer(self):
        """Next action items have pointer cursor in JS."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        # Find WP-193 comment and check nearby code
        wp193_pos = js.index("WP-193")
        section = js[wp193_pos:wp193_pos + 2000]
        assert "cursor" in section and "pointer" in section

    def test_next_action_scroll_into_view(self):
        """Click handler scrolls to section."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        wp193_pos = js.index("WP-193")
        section = js[wp193_pos:wp193_pos + 2000]
        assert "scrollIntoView" in section

    def test_section_map_defined(self):
        """Section name to heading ID map is defined."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        wp193_pos = js.index("WP-193")
        section = js[wp193_pos:wp193_pos + 2000]
        assert "sectionMap" in section
        assert "opp-title" in section
        assert "conv-title" in section
        assert "leads-title" in section

    def test_next_action_css_hover(self):
        """Next action items have hover styles."""
        with open("app/operator_ui/styles.css") as f:
            css = f.read()
        assert ".next-action-item:hover" in css

    def test_next_action_css_cursor(self):
        """Next action items have cursor pointer in CSS."""
        with open("app/operator_ui/styles.css") as f:
            css = f.read()
        na_section = css.split(".next-action-item {")[1].split("}")[0]
        assert "cursor" in na_section

    def test_next_action_title_tooltip(self):
        """Next action items have tooltip title."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        wp193_pos = js.index("WP-193")
        section = js[wp193_pos:wp193_pos + 2000]
        assert "Clique para ir para" in section

    def test_section_map_has_tasks(self):
        """Section map includes internal tasks."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        wp193_pos = js.index("WP-193")
        section = js[wp193_pos:wp193_pos + 2000]
        assert "tasks-title" in section

    def test_section_map_has_review_queue(self):
        """Section map includes review queue."""
        with open("app/operator_ui/app.js") as f:
            js = f.read()
        wp193_pos = js.index("WP-193")
        section = js[wp193_pos:wp193_pos + 2000]
        assert "rq-title" in section

    def test_next_action_transition(self):
        """Next action items have smooth transition."""
        with open("app/operator_ui/styles.css") as f:
            css = f.read()
        na_section = css.split(".next-action-item {")[1].split("}")[0]
        assert "transition" in na_section

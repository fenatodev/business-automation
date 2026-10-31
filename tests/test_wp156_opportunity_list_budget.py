"""WP-156 — Exibir orçamento e descrição na lista de oportunidades.

Testa que renderList() inclui budget, deadline e descrição truncada
nos elementos criados dinamicamente.
"""

import json
import pathlib


class TestOpportunityListBudget:
    """Verify opportunity list shows budget, deadline, and description preview."""

    @classmethod
    def setup_class(cls):
        cls.app_js = pathlib.Path("app/operator_ui/app.js").read_text()
        cls.styles_css = pathlib.Path("app/operator_ui/styles.css").read_text()

    def test_renderList_creates_title_row(self):
        """renderList wraps title and badge in opp-item-title-row."""
        assert "opp-item-title-row" in self.app_js
        assert "titleRow.className = " in self.app_js

    def test_renderList_shows_description_preview(self):
        """renderList adds description preview when description exists."""
        assert "opp-item-description" in self.app_js
        assert "opportunity.description" in self.app_js

    def test_renderList_truncates_long_description(self):
        """Long descriptions are truncated to 120 characters."""
        assert "120" in self.app_js
        assert "substring(0, 120)" in self.app_js

    def test_renderList_shows_budget(self):
        """Budget is displayed when present."""
        assert "opp-item-budget" in self.app_js
        assert "opportunity.budget" in self.app_js

    def test_renderList_shows_deadline(self):
        """Deadline is displayed when present."""
        assert "opp-item-deadline" in self.app_js
        assert "opportunity.deadline" in self.app_js

    def test_renderList_meta_row(self):
        """Budget and deadline are grouped in opp-item-meta."""
        assert "opp-item-meta" in self.app_js

    def test_renderList_budget_deadline_conditional(self):
        """Meta row is only created when budget or deadline exists."""
        assert "if (opportunity.budget || opportunity.deadline)" in self.app_js

    def test_renderList_description_conditional(self):
        """Description preview is only added when description exists."""
        assert "if (opportunity.description)" in self.app_js

    def test_css_title_row_flex(self):
        """CSS defines opp-item-title-row as flex container."""
        assert ".opp-item-title-row" in self.styles_css
        assert "display: flex" in self.styles_css

    def test_css_description_preview(self):
        """CSS styles opp-item-description with truncation."""
        assert ".opp-item-description" in self.styles_css
        assert "text-overflow: ellipsis" in self.styles_css

    def test_css_meta_row(self):
        """CSS defines opp-item-meta flex layout."""
        assert ".opp-item-meta" in self.styles_css

    def test_css_budget_color(self):
        """Budget has distinct color."""
        assert ".opp-item-budget" in self.styles_css

    def test_css_deadline_color(self):
        """Deadline has distinct color."""
        assert ".opp-item-deadline" in self.styles_css

    def test_no_innerhtml_used(self):
        """XSS rule: no innerHTML in renderList changes."""
        # The new code uses textContent and createElement, not innerHTML
        snippet_start = self.app_js.find("opp-item-title-row")
        snippet_end = self.app_js.find("button.addEventListener", snippet_start)
        snippet = self.app_js[snippet_start:snippet_end]
        assert "innerHTML" not in snippet

    def test_budget_emoji_indicator(self):
        """Budget line includes emoji for visual clarity."""
        assert "💰" in self.app_js

    def test_deadline_emoji_indicator(self):
        """Deadline line includes emoji for visual clarity."""
        assert "📅" in self.app_js

"""WP-276: Test opportunity progress bar in operator UI."""

import os

UI_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "operator_ui")
HTML = open(os.path.join(UI_DIR, "index.html"), encoding="utf-8").read()
JS = open(os.path.join(UI_DIR, "app.js"), encoding="utf-8").read()
CSS = open(os.path.join(UI_DIR, "styles.css"), encoding="utf-8").read()


class TestOpportunityProgressBar:
    """Verify progress bar implementation."""

    def test_html_has_progress_container(self):
        """HTML has progress bar container."""
        assert 'id="opp-progress"' in HTML
        assert 'class="opp-progress"' in HTML

    def test_html_has_progress_fill(self):
        """HTML has progress fill element."""
        assert 'id="opp-progress-fill"' in HTML
        assert 'class="opp-progress-fill"' in HTML

    def test_html_has_progress_percent(self):
        """HTML has progress percent label."""
        assert 'id="opp-progress-percent"' in HTML

    def test_html_has_progress_label(self):
        """HTML has progress label text."""
        assert "Progresso do ciclo" in HTML

    def test_js_has_updateOppProgress_function(self):
        """JS has updateOppProgress function."""
        assert "function updateOppProgress" in JS

    def test_js_progress_map_pending(self):
        """Progress map includes pending."""
        assert "pending: 10" in JS

    def test_js_progress_map_follow(self):
        """Progress map includes follow."""
        assert "follow: 25" in JS

    def test_js_progress_map_prepare_proposal(self):
        """Progress map includes prepare_proposal."""
        assert "prepare_proposal: 40" in JS

    def test_js_progress_map_in_progress(self):
        """Progress map includes in_progress."""
        assert "in_progress: 70" in JS

    def test_js_progress_map_done(self):
        """Progress map includes done at 100%."""
        assert "done: 100" in JS

    def test_js_progress_map_lost(self):
        """Progress map includes lost."""
        assert "lost: 50" in JS

    def test_js_progress_map_ignore(self):
        """Progress map includes ignore."""
        assert "ignore: 50" in JS

    def test_js_calls_updateOppProgress_on_select(self):
        """selectOpportunity calls updateOppProgress."""
        assert "updateOppProgress(record.next_action)" in JS

    def test_js_sets_width_style(self):
        """JS sets width style on progress fill."""
        assert 'style.width' in JS
        assert 'opp-progress-fill' in JS

    def test_js_sets_percent_text(self):
        """JS sets percent text content."""
        assert 'opp-progress-percent' in JS
        assert 'textContent' in JS

    def test_css_has_progress_bar_styles(self):
        """CSS has progress bar styles."""
        assert ".opp-progress" in CSS
        assert ".opp-progress-bar" in CSS
        assert ".opp-progress-fill" in CSS

    def test_css_has_progress_label_styles(self):
        """CSS has progress label styles."""
        assert ".opp-progress-label" in CSS

    def test_css_has_transition(self):
        """CSS has transition for smooth animation."""
        assert "transition" in CSS
        assert "width" in CSS

    def test_css_has_gradient_background(self):
        """CSS has gradient background for visual appeal."""
        assert "linear-gradient" in CSS

    def test_progress_bar_positioned_in_detail_panel(self):
        """Progress bar is in the selection panel, before metadata."""
        idx_progress = HTML.index('id="opp-progress"')
        idx_metadata = HTML.index('class="metadata"')
        assert idx_progress < idx_metadata

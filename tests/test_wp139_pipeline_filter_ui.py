"""WP-139 — Pipeline filter chips UI contract tests.

Verifies that the operator UI has pipeline filter chips that allow filtering
opportunities by status (next_action), with counts from pipeline-summary.
"""

import pytest


class TestPipelineFilterUI:
    """Verify pipeline filter chips are properly connected."""

    def _get_app_js(self):
        with open("app/operator_ui/app.js") as f:
            return f.read()

    def _get_index_html(self):
        with open("app/operator_ui/index.html") as f:
            return f.read()

    def _get_styles_css(self):
        with open("app/operator_ui/styles.css") as f:
            return f.read()

    # --- HTML: pipeline container ---

    def test_pipeline_container_exists(self):
        """HTML should have opp-pipeline container."""
        html = self._get_index_html()
        assert 'id="opp-pipeline"' in html

    def test_pipeline_chips_exist(self):
        """HTML should have pipeline chips for all statuses."""
        html = self._get_index_html()
        assert 'data-pipeline="all"' in html
        assert 'data-pipeline="pending"' in html
        assert 'data-pipeline="follow"' in html
        assert 'data-pipeline="prepare_proposal"' in html
        assert 'data-pipeline="in_progress"' in html
        assert 'data-pipeline="done"' in html
        assert 'data-pipeline="lost"' in html

    def test_pipeline_count_spans_exist(self):
        """HTML should have count spans for each status."""
        html = self._get_index_html()
        assert 'data-count="pending"' in html
        assert 'data-count="follow"' in html
        assert 'data-count="prepare_proposal"' in html
        assert 'data-count="in_progress"' in html
        assert 'data-count="done"' in html
        assert 'data-count="lost"' in html

    # --- JavaScript: state ---

    def test_opp_pipeline_filter_state(self):
        """app.js should have oppPipelineFilter state variable."""
        js = self._get_app_js()
        assert "oppPipelineFilter" in js

    def test_opp_pipeline_filter_defaults_to_all(self):
        """oppPipelineFilter should default to 'all'."""
        js = self._get_app_js()
        assert 'oppPipelineFilter = "all"' in js

    # --- JavaScript: refreshList uses pipeline filter ---

    def test_refresh_list_uses_pipeline_filter(self):
        """refreshList should include next_action param when filter is set."""
        js = self._get_app_js()
        assert "oppPipelineFilter" in js
        assert "next_action=" in js

    # --- JavaScript: pipeline-summary call ---

    def test_refresh_list_calls_pipeline_summary(self):
        """refreshList should call /opportunities/pipeline-summary."""
        js = self._get_app_js()
        assert "/opportunities/pipeline-summary" in js

    # --- JavaScript: update pipeline counts ---

    def test_update_pipeline_counts(self):
        """refreshList should update pipeline count elements."""
        js = self._get_app_js()
        assert "data-count" in js

    # --- JavaScript: highlight active chip ---

    def test_highlight_active_chip(self):
        """refreshList should highlight the active pipeline chip."""
        js = self._get_app_js()
        assert "opp-pipeline-chip" in js
        assert "'active'" in js or '"active"' in js

    # --- JavaScript: event listeners ---

    def test_pipeline_chip_click_listener(self):
        """Pipeline chips should have click listeners."""
        js = self._get_app_js()
        assert "opp-pipeline-chip" in js
        assert "data-pipeline" in js

    def test_pipeline_filter_resets_offset(self):
        """Changing pipeline filter should reset oppOffset to 0."""
        js = self._get_app_js()
        # Find the pipeline chip listener
        assert "oppOffset = 0" in js

    # --- JavaScript: disconnect cleanup ---

    def test_disconnect_resets_pipeline_filter(self):
        """disconnect should reset oppPipelineFilter to 'all'."""
        js = self._get_app_js()
        start = js.find("function disconnect(")
        assert start != -1, "disconnect function not found"
        end = js.find("\n}", start + 500)
        func_body = js[start:end] if end != -1 else js[start:start+800]
        assert 'oppPipelineFilter = "all"' in func_body, (
            "disconnect should reset oppPipelineFilter"
        )

    # --- JavaScript: allowlist ---

    def test_api_allows_pipeline_summary(self):
        """api() allowlist should allow /opportunities/pipeline-summary."""
        js = self._get_app_js()
        assert "pipeline-summary" in js

    # --- CSS ---

    def test_pipeline_css_exists(self):
        """styles.css should have .opp-pipeline styles."""
        css = self._get_styles_css()
        assert ".opp-pipeline" in css

    def test_pipeline_chip_css_exists(self):
        """styles.css should have .opp-pipeline-chip styles."""
        css = self._get_styles_css()
        assert ".opp-pipeline-chip" in css

    def test_pipeline_chip_active_css_exists(self):
        """styles.css should have .opp-pipeline-chip.active styles."""
        css = self._get_styles_css()
        assert ".opp-pipeline-chip.active" in css

    def test_pipeline_count_css_exists(self):
        """styles.css should have .opp-pipeline-count styles."""
        css = self._get_styles_css()
        assert ".opp-pipeline-count" in css

    # --- HTML: pipeline in correct location ---

    def test_pipeline_after_toolbar(self):
        """opp-pipeline should be after opp-toolbar."""
        html = self._get_index_html()
        toolbar_pos = html.find('class="opp-toolbar"')
        pipeline_pos = html.find('id="opp-pipeline"')
        assert toolbar_pos != -1 and pipeline_pos != -1
        assert pipeline_pos > toolbar_pos, "Pipeline should be after toolbar"

    def test_pipeline_before_list(self):
        """opp-pipeline should be before opportunity-list."""
        html = self._get_index_html()
        pipeline_pos = html.find('id="opp-pipeline"')
        list_pos = html.find('id="opportunity-list"')
        assert pipeline_pos != -1 and list_pos != -1
        assert pipeline_pos < list_pos, "Pipeline should be before list"

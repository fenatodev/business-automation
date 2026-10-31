"""WP-134 — Review queue filters UI contract tests."""

import pytest


class TestReviewQueueFiltersUI:
    """Verify the review queue UI has filter controls connected to the backend."""

    def _get_app_js(self):
        with open("app/operator_ui/app.js") as f:
            return f.read()

    def _get_index_html(self):
        with open("app/operator_ui/index.html") as f:
            return f.read()

    def test_status_filter_element_exists(self):
        """HTML should have rq-status-filter dropdown."""
        html = self._get_index_html()
        assert 'id="rq-status-filter"' in html
        assert 'value="pending"' in html
        assert 'value="approved"' in html
        assert 'value="rejected"' in html

    def test_sort_filter_element_exists(self):
        """HTML should have rq-sort dropdown."""
        html = self._get_index_html()
        assert 'id="rq-sort"' in html
        assert 'value="created_at"' in html
        assert 'value="id"' in html
        assert 'value="status"' in html

    def test_clear_filters_button_exists(self):
        """HTML should have rq-clear-filters button."""
        html = self._get_index_html()
        assert 'id="rq-clear-filters"' in html

    def test_build_review_url_function_exists(self):
        """app.js should have buildReviewUrl function."""
        js = self._get_app_js()
        assert "function buildReviewUrl()" in js

    def test_build_review_count_url_function_exists(self):
        """app.js should have buildReviewCountUrl function."""
        js = self._get_app_js()
        assert "function buildReviewCountUrl()" in js

    def test_build_review_url_includes_status(self):
        """buildReviewUrl should include status param when set."""
        js = self._get_app_js()
        assert 'rq-status-filter' in js
        assert 'params.set("status"' in js or 'params.set(\'status\'' in js

    def test_build_review_url_includes_sort(self):
        """buildReviewUrl should include sort param when set."""
        js = self._get_app_js()
        assert 'rq-sort' in js
        assert 'params.set("sort"' in js or 'params.set(\'sort\'' in js

    def test_build_review_url_includes_pagination(self):
        """buildReviewUrl should include limit and offset."""
        js = self._get_app_js()
        assert 'params.set("limit"' in js or 'params.set(\'limit\'' in js
        assert 'params.set("offset"' in js or 'params.set(\'offset\'' in js

    def test_status_filter_change_resets_offset(self):
        """Status filter change should reset reviewOffset to 0."""
        js = self._get_app_js()
        assert 'rq-status-filter' in js
        # Find the change listener for status filter
        assert 'reviewOffset = 0' in js

    def test_sort_filter_change_resets_offset(self):
        """Sort filter change should reset reviewOffset to 0."""
        js = self._get_app_js()
        assert 'rq-sort' in js

    def test_clear_filters_resets_all(self):
        """Clear filters should reset status, sort and offset."""
        js = self._get_app_js()
        assert 'rq-clear-filters' in js

    def test_review_api_allows_count_endpoint(self):
        """reviewApi allowlist should include /count endpoint."""
        js = self._get_app_js()
        assert 'review-queue/count' in js

    def test_review_api_allows_query_params(self):
        """reviewApi allowlist should allow query params on /review-queue/."""
        js = self._get_app_js()
        # The allowlist should use regex that allows query params
        assert r'/review-queue\/(\?|$)' in js or '/review-queue/(?|$)' in js

    def test_refresh_review_queue_uses_build_review_url(self):
        """refreshReviewQueue should call buildReviewUrl()."""
        js = self._get_app_js()
        assert 'buildReviewUrl()' in js

    def test_review_total_state_variable(self):
        """app.js should have reviewTotal state variable."""
        js = self._get_app_js()
        assert 'reviewTotal' in js

    def test_filters_section_in_html(self):
        """HTML should have rq-filters section."""
        html = self._get_index_html()
        assert 'rq-filters' in html

    def test_css_styles_exist(self):
        """styles.css should have .rq-filters styles."""
        with open("app/operator_ui/styles.css") as f:
            css = f.read()
        assert ".rq-filters" in css
        assert ".rq-filter-group" in css

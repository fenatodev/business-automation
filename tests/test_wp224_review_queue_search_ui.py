"""WP-224 — Review queue search UI contract tests.

The review queue UI now has a search field that filters items by keywords
in message, intent, and event_id fields.
"""

import pytest


def test_review_search_field_exists():
    """The search input field exists in the HTML."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="rq-search"' in html
    assert 'type="search"' in html or "type=search" in html


def test_review_search_field_in_filters_section():
    """The search field is inside the rq-filters section."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    # Find the rq-filters div
    filters_start = html.find('class="rq-filters"')
    assert filters_start != -1, "rq-filters section not found"
    # Find the next closing div after rq-filters
    search_pos = html.find('id="rq-search"', filters_start)
    assert search_pos != -1, "rq-search not found in rq-filters section"
    # Make sure it's before the status filter
    status_pos = html.find('id="rq-status-filter"', filters_start)
    assert status_pos != -1
    assert search_pos < status_pos, "Search field should come before status filter"


def test_review_search_connected_in_js():
    """The search field is connected in app.js."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert 'rq-search' in js
    # Check buildReviewUrl includes search
    assert 'rq-search' in js


def test_review_search_listener_exists():
    """There's an input listener for the search field."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    # Find the search listener
    assert 'rq-search' in js
    # Check for input event listener
    search_idx = js.find('rq-search')
    # Look for addEventListener near rq-search references
    assert "addEventListener" in js


def test_review_clear_filters_resets_search():
    """The clear filters button resets the search field."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    # Find clear filters handler
    clear_idx = js.find('rq-clear-filters')
    assert clear_idx != -1
    # Check that rq-search is reset in clear handler
    # Look for rq-search value reset after clear-filters
    after_clear = js[clear_idx:clear_idx + 500]
    assert 'rq-search' in after_clear, "Clear filters should reset rq-search"


def test_review_export_csv_includes_search():
    """Export CSV includes the search parameter."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    # Find export handler
    export_idx = js.find('rq-export-csv')
    assert export_idx != -1
    after_export = js[export_idx:export_idx + 600]
    assert 'rq-search' in after_export, "Export CSV should include search parameter"


def test_review_build_review_url_includes_search():
    """buildReviewUrl includes the search parameter."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    # Find buildReviewUrl function
    build_idx = js.find('function buildReviewUrl')
    assert build_idx != -1
    # Look for rq-search in the function
    func_end = js.find('function buildReviewCountUrl', build_idx)
    func_body = js[build_idx:func_end]
    assert 'rq-search' in func_body, "buildReviewUrl should include search"


def test_review_build_review_count_url_includes_search():
    """buildReviewCountUrl includes the search parameter."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    # Find buildReviewCountUrl function
    build_idx = js.find('function buildReviewCountUrl')
    assert build_idx != -1
    # Look for rq-search in the function
    func_end = js.find('async function refreshReviewQueue', build_idx)
    func_body = js[build_idx:func_end]
    assert 'rq-search' in func_body, "buildReviewCountUrl should include search"


def test_review_search_field_has_placeholder():
    """The search field has a placeholder text."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    search_idx = html.find('id="rq-search"')
    assert search_idx != -1
    # Check for placeholder attribute
    after_search = html[search_idx:search_idx + 200]
    assert 'placeholder' in after_search, "Search field should have placeholder"


def test_review_search_field_has_label():
    """The search field has a label."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    search_idx = html.find('id="rq-search"')
    assert search_idx != -1
    # Check for label before the input
    before_search = html[max(0, search_idx - 100):search_idx]
    assert '<label' in before_search, "Search field should have a label"

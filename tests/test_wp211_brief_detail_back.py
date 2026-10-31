"""WP-211 — Back button and title in brief detail panel.

The brief detail panel (WP-187) had no back button and no visible title.
Added a header row with back button and dynamic title, plus CSS styles.
"""


def test_brief_detail_has_back_button():
    """The brief detail panel has a back button."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="brief-detail-back"' in html


def test_brief_detail_back_button_text():
    """The back button has 'Voltar' text."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="brief-detail-back"')
    btn = html[start:start+100]
    assert "Voltar" in btn


def test_brief_detail_has_title_element():
    """The brief detail panel has a title h3 element."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="brief-detail-title"' in html


def test_brief_detail_has_header_row():
    """The brief detail panel has a header div."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'class="detail-panel-header"' in html


def test_brief_detail_header_structure():
    """The header contains back button and title."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    header_start = html.index('class="detail-panel-header"')
    header_end = html.index('</div>', header_start)
    header = html[header_start:header_end]
    assert 'brief-detail-back' in header
    assert 'brief-detail-title' in header


def test_brief_detail_header_before_content():
    """The header appears before the content area."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    header_pos = html.index('class="detail-panel-header"')
    content_pos = html.index('id="brief-detail-content"')
    assert header_pos < content_pos


def test_app_js_sets_brief_title():
    """app.js sets the brief detail title in selectBrief."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert 'brief-detail-title' in js
    # Find where title is set
    title_idx = js.index('brief-detail-title')
    nearby = js[title_idx:title_idx+100]
    assert 'textContent' in nearby


def test_app_js_back_button_handler():
    """app.js has a click handler for the back button."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert 'brief-detail-back' in js
    # Find the handler
    back_idx = js.index('brief-detail-back')
    nearby = js[back_idx:back_idx+200]
    assert 'addEventListener' in nearby or 'click' in nearby


def test_app_js_back_button_hides_detail():
    """The back button handler hides the detail panel."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    back_idx = js.index('brief-detail-back')
    nearby = js[back_idx:back_idx+200]
    assert 'hidden = true' in nearby or '.hidden=true' in nearby


def test_css_has_detail_panel_header():
    """CSS has styles for .detail-panel-header."""
    with open("app/operator_ui/styles.css") as f:
        css = f.read()
    assert '.detail-panel-header' in css


def test_css_header_has_flex_layout():
    """The header uses flexbox layout."""
    with open("app/operator_ui/styles.css") as f:
        css = f.read()
    start = css.index('.detail-panel-header')
    end = css.index('}', start)
    block = css[start:end]
    assert 'display: flex' in block


def test_css_header_has_border():
    """The header has a bottom border separator."""
    with open("app/operator_ui/styles.css") as f:
        css = f.read()
    start = css.index('.detail-panel-header')
    end = css.index('}', start)
    block = css[start:end]
    assert 'border-bottom' in block


def test_css_header_h3_styles():
    """CSS has styles for header h3 element."""
    with open("app/operator_ui/styles.css") as f:
        css = f.read()
    assert '.detail-panel-header h3' in css


def test_css_header_button_styles():
    """CSS has styles for header button element."""
    with open("app/operator_ui/styles.css") as f:
        css = f.read()
    assert '.detail-panel-header button' in css


def test_brief_detail_panel_structure():
    """The brief detail panel has header and content sections."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    detail_start = html.index('id="brief-detail"')
    detail_end = html.index('</div>', html.index('brief-detail-content', detail_start))
    detail = html[detail_start:detail_end]
    assert 'detail-panel-header' in detail
    assert 'brief-detail-back' in detail
    assert 'brief-detail-title' in detail
    assert 'brief-detail-content' in detail


def test_back_button_is_type_button():
    """The back button has type='button' to prevent form submission."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="brief-detail-back"')
    btn = html[start:start+100]
    assert 'type="button"' in btn


def test_selectBrief_sets_title_with_opportunity_name():
    """selectBrief sets title using the opportunity title parameter."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    # Find selectBrief function
    func_start = js.index('async function selectBrief')
    func_end = js.index('}', func_start + 500)
    func = js[func_start:func_end]
    assert 'brief-detail-title' in func
    assert 'textContent' in func


def test_brief_detail_back_in_wp_comment():
    """The back button handler is marked with WP-211 comment."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert 'WP-211' in js


def test_css_wp211_comment():
    """The CSS has WP-211 comment for the header styles."""
    with open("app/operator_ui/styles.css") as f:
        css = f.read()
    assert 'WP-211' in css

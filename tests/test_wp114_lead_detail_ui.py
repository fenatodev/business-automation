"""WP-114 — Detalhes expandidos de lead via UI."""

import pytest


@pytest.fixture
def ui_files():
    """Read the operator UI files."""
    import pathlib
    base = pathlib.Path("app/operator_ui")
    return {
        "html": (base / "index.html").read_text(),
        "js": (base / "app.js").read_text(),
        "css": (base / "styles.css").read_text(),
    }


# --- HTML elements ---


def test_lead_detail_panel_exists(ui_files):
    assert 'id="lead-detail"' in ui_files["html"]


def test_lead_detail_name_exists(ui_files):
    assert 'id="lead-detail-name"' in ui_files["html"]


def test_lead_detail_status_exists(ui_files):
    assert 'id="lead-detail-status"' in ui_files["html"]


def test_lead_detail_info_exists(ui_files):
    assert 'id="lead-detail-info"' in ui_files["html"]


def test_lead_detail_back_button_exists(ui_files):
    assert 'id="lead-detail-back"' in ui_files["html"]


def test_lead_conversations_list_exists(ui_files):
    assert 'id="lead-conversations-list"' in ui_files["html"]


def test_lead_detail_in_leads_section(ui_files):
    html = ui_files["html"]
    section_start = html.index('aria-labelledby="leads-title"')
    section_end = html.index('</section>', section_start)
    section = html[section_start:section_end]
    assert 'id="lead-detail"' in section


# --- JavaScript behavior ---


def test_show_lead_detail_function_exists(ui_files):
    assert "showLeadDetail" in ui_files["js"]


def test_hide_lead_detail_function_exists(ui_files):
    assert "hideLeadDetail" in ui_files["js"]


def test_lead_detail_back_handler_exists(ui_files):
    assert "lead-detail-back" in ui_files["js"]


def test_lead_click_listener_in_render_leads(ui_files):
    js = ui_files["js"]
    # renderLeads should add click listener
    start = js.index("function renderLeads")
    end = min(start + 5000, len(js))
    func = js[start:end]
    assert "showLeadDetail" in func


def test_lead_detail_populates_name(ui_files):
    js = ui_files["js"]
    start = js.index("async function showLeadDetail")
    end = min(start + 1500, len(js))
    func = js[start:end]
    assert "lead-detail-name" in func


def test_lead_detail_populates_status(ui_files):
    js = ui_files["js"]
    start = js.index("async function showLeadDetail")
    end = min(start + 1500, len(js))
    func = js[start:end]
    assert "lead-detail-status" in func


def test_lead_detail_loads_conversations(ui_files):
    js = ui_files["js"]
    start = js.index("async function showLeadDetail")
    end = min(start + 1500, len(js))
    func = js[start:end]
    assert "lead-conversations-list" in func


def test_hide_lead_detail_shows_list(ui_files):
    js = ui_files["js"]
    start = js.index("function hideLeadDetail")
    end = min(start + 500, len(js))
    func = js[start:end]
    assert "leads-list" in func


# --- CSS styles ---


def test_lead_detail_css_exists(ui_files):
    assert ".lead-detail" in ui_files["css"]


def test_lead_detail_header_css_exists(ui_files):
    assert ".lead-detail-header" in ui_files["css"]


def test_lead_detail_info_css_exists(ui_files):
    assert ".lead-detail-info" in ui_files["css"]

"""WP-112 — Criar lead manualmente via UI."""

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


def test_create_lead_form_exists(ui_files):
    assert 'id="create-lead-form"' in ui_files["html"]


def test_new_lead_name_input_exists(ui_files):
    assert 'id="new-lead-name"' in ui_files["html"]


def test_new_lead_phone_input_exists(ui_files):
    assert 'id="new-lead-phone"' in ui_files["html"]


def test_new_lead_source_input_exists(ui_files):
    assert 'id="new-lead-source"' in ui_files["html"]


def test_new_lead_interest_input_exists(ui_files):
    assert 'id="new-lead-interest"' in ui_files["html"]


def test_cancel_create_lead_button_exists(ui_files):
    assert 'id="cancel-create-lead"' in ui_files["html"]


def test_show_create_lead_button_exists(ui_files):
    assert 'id="show-create-lead"' in ui_files["html"]


def test_create_lead_form_in_leads_section(ui_files):
    html = ui_files["html"]
    section_start = html.index('aria-labelledby="leads-title"')
    section_end = html.index('</section>', section_start)
    section = html[section_start:section_end]
    assert 'id="create-lead-form"' in section


# --- JavaScript behavior ---


def test_create_lead_function_exists(ui_files):
    assert "createLead" in ui_files["js"]


def test_create_lead_uses_post_method(ui_files):
    js = ui_files["js"]
    start = js.index("async function createLead")
    end = js.index("return res.json()", start) + len("return res.json()")
    func = js[start:end]
    assert 'POST' in func


def test_show_create_lead_handler_exists(ui_files):
    assert 'show-create-lead' in ui_files["js"]


def test_cancel_create_lead_handler_exists(ui_files):
    assert 'cancel-create-lead' in ui_files["js"]


def test_create_lead_form_submit_handler_exists(ui_files):
    assert 'create-lead-form' in ui_files["js"]


def test_create_lead_validates_name_required(ui_files):
    js = ui_files["js"]
    assert 'Nome é obrigatório' in js


def test_create_lead_refreshes_list_after_save(ui_files):
    js = ui_files["js"]
    assert 'refreshLeads' in js


def test_create_lead_clears_form_after_save(ui_files):
    js = ui_files["js"]
    assert 'new-lead-name' in js
    assert '.value = ""' in js


def test_create_lead_defaults_source_to_manual(ui_files):
    js = ui_files["js"]
    assert '"manual"' in js

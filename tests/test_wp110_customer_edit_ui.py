"""WP-110 — Editar customer via UI."""

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


def test_customer_edit_form_exists(ui_files):
    assert 'id="customer-edit-form"' in ui_files["html"]


def test_customer_edit_name_input_exists(ui_files):
    assert 'id="customer-edit-name"' in ui_files["html"]


def test_customer_edit_phone_input_exists(ui_files):
    assert 'id="customer-edit-phone"' in ui_files["html"]


def test_customer_edit_email_input_exists(ui_files):
    assert 'id="customer-edit-email"' in ui_files["html"]


def test_customer_edit_cancel_button_exists(ui_files):
    assert 'id="customer-edit-cancel"' in ui_files["html"]


def test_customer_edit_form_in_detail_section(ui_files):
    html = ui_files["html"]
    detail_start = html.index('id="customer-detail"')
    section_end = html.index('</section>', detail_start)
    detail_section = html[detail_start:section_end]
    assert 'id="customer-edit-form"' in detail_section


# --- JavaScript behavior ---


def test_show_customer_edit_form_function_exists(ui_files):
    assert "showCustomerEditForm" in ui_files["js"]


def test_hide_customer_edit_form_function_exists(ui_files):
    assert "hideCustomerEditForm" in ui_files["js"]


def test_update_customer_function_exists(ui_files):
    assert "updateCustomer" in ui_files["js"]


def test_update_customer_uses_patch_method(ui_files):
    js = ui_files["js"]
    # Find the updateCustomer function
    start = js.index("async function updateCustomer")
    end = js.index("}", start)
    func = js[start:end]
    assert 'PATCH' in func


def test_edit_cancel_handler_exists(ui_files):
    assert 'customer-edit-cancel' in ui_files["js"]


def test_edit_form_submit_handler_exists(ui_files):
    assert 'customer-edit-form' in ui_files["js"]
    assert "addEventListener" in ui_files["js"]


def test_edit_button_added_in_show_customer_detail(ui_files):
    js = ui_files["js"]
    # The showCustomerDetail function should create an edit button
    assert 'customer-edit-btn' in js


def test_edit_form_populates_fields(ui_files):
    js = ui_files["js"]
    assert 'customer-edit-name' in js
    assert 'customer-edit-phone' in js
    assert 'customer-edit-email' in js


def test_edit_form_validates_name_required(ui_files):
    js = ui_files["js"]
    assert 'Nome é obrigatório' in js


def test_edit_form_refreshes_list_after_save(ui_files):
    js = ui_files["js"]
    # After saving, should refresh the list
    assert 'refreshCustomers' in js

"""WP-111 — Criar customer manualmente via UI."""

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


def test_create_customer_form_exists(ui_files):
    assert 'id="create-customer-form"' in ui_files["html"]


def test_new_customer_name_input_exists(ui_files):
    assert 'id="new-customer-name"' in ui_files["html"]


def test_new_customer_phone_input_exists(ui_files):
    assert 'id="new-customer-phone"' in ui_files["html"]


def test_new_customer_email_input_exists(ui_files):
    assert 'id="new-customer-email"' in ui_files["html"]


def test_cancel_create_customer_button_exists(ui_files):
    assert 'id="cancel-create-customer"' in ui_files["html"]


def test_show_create_customer_button_exists(ui_files):
    assert 'id="show-create-customer"' in ui_files["html"]


def test_create_customer_form_in_customers_section(ui_files):
    html = ui_files["html"]
    section_start = html.index('aria-labelledby="customers-title"')
    section_end = html.index('</section>', section_start)
    section = html[section_start:section_end]
    assert 'id="create-customer-form"' in section


# --- JavaScript behavior ---


def test_create_customer_function_exists(ui_files):
    assert "createCustomer" in ui_files["js"]


def test_create_customer_uses_post_method(ui_files):
    js = ui_files["js"]
    start = js.index("async function createCustomer")
    # Find the complete function body (look for the fetch call)
    end = js.index("return res.json()", start) + len("return res.json()")
    func = js[start:end]
    assert 'POST' in func


def test_show_create_customer_handler_exists(ui_files):
    assert 'show-create-customer' in ui_files["js"]


def test_cancel_create_customer_handler_exists(ui_files):
    assert 'cancel-create-customer' in ui_files["js"]


def test_create_customer_form_submit_handler_exists(ui_files):
    assert 'create-customer-form' in ui_files["js"]


def test_create_customer_validates_name_required(ui_files):
    js = ui_files["js"]
    assert 'Nome é obrigatório' in js


def test_create_customer_refreshes_list_after_save(ui_files):
    js = ui_files["js"]
    assert 'refreshCustomers' in js


def test_create_customer_clears_form_after_save(ui_files):
    js = ui_files["js"]
    assert 'new-customer-name' in js
    assert '.value = ""' in js

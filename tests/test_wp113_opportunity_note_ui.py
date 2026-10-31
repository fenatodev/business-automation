"""WP-113 — Notas em oportunidades via UI."""

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


def test_opp_note_panel_exists(ui_files):
    assert 'id="opp-note-panel"' in ui_files["html"]


def test_opp_note_textarea_exists(ui_files):
    assert 'id="opp-note"' in ui_files["html"]


def test_save_opp_note_button_exists(ui_files):
    assert 'id="save-opp-note"' in ui_files["html"]


def test_opp_note_panel_in_selection_section(ui_files):
    html = ui_files["html"]
    panel_start = html.index('id="selection-panel"')
    section_end = html.index('</section>', panel_start)
    section = html[panel_start:section_end]
    assert 'id="opp-note-panel"' in section


def test_opp_note_label_exists(ui_files):
    assert 'for="opp-note"' in ui_files["html"]


# --- JavaScript behavior ---


def test_save_opp_note_handler_exists(ui_files):
    assert "save-opp-note" in ui_files["js"]


def test_save_opp_note_uses_patch_method(ui_files):
    js = ui_files["js"]
    start = js.index('$("save-opp-note")')
    end = js.index("});", start) + len("});")
    handler = js[start:end]
    assert "PATCH" in handler


def test_save_opp_note_sends_triage_note(ui_files):
    js = ui_files["js"]
    start = js.index('$("save-opp-note")')
    end = js.index("});", start) + len("});")
    handler = js[start:end]
    assert "triage_note" in handler


def test_opp_note_populated_in_select_opportunity(ui_files):
    js = ui_files["js"]
    # The selectOpportunity function should populate opp-note
    start = js.index("async function selectOpportunity")
    end = js.index("}", start)
    # Find the closing brace of the function (may need to go further)
    depth = 0
    i = start
    while i < len(js):
        if js[i] == "{":
            depth += 1
        elif js[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
        i += 1
    func = js[start:end]
    assert "opp-note" in func


def test_save_opp_note_syncs_triage_note_field(ui_files):
    """Saving note should also update the triage-note field in the triage form."""
    js = ui_files["js"]
    start = js.index('$("save-opp-note")')
    # Extend far enough to capture the full handler
    end = min(start + 800, len(js))
    handler = js[start:end]
    assert "triage-note" in handler


def test_save_opp_note_updates_in_memory_list(ui_files):
    js = ui_files["js"]
    start = js.index('$("save-opp-note")')
    end = js.index("});", start) + len("});")
    handler = js[start:end]
    assert "findIndex" in handler or "opportunities" in handler


# --- CSS styles ---


def test_opp_note_panel_css_exists(ui_files):
    assert ".opp-note-panel" in ui_files["css"]


def test_opp_note_panel_has_textarea_style(ui_files):
    css = ui_files["css"]
    start = css.index(".opp-note-panel")
    end = css.index("/*", start + len(".opp-note-panel"))
    styles = css[start:end]
    assert "textarea" in styles

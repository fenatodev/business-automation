"""WP-108 — Painel de detalhes da oportunidade.

Testes de contrato UI: verifica que os novos elementos HTML e JavaScript
estão presentes e funcionais. Sem backend modificado.
"""

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


def test_selected_source_element_exists(ui_files):
    assert 'id="selected-source"' in ui_files["html"]


def test_selected_captured_at_element_exists(ui_files):
    assert 'id="selected-captured-at"' in ui_files["html"]


def test_selected_triage_note_element_exists(ui_files):
    assert 'id="selected-triage-note"' in ui_files["html"]


def test_view_brief_button_exists(ui_files):
    assert 'id="view-brief-button"' in ui_files["html"]


def test_opp_detail_actions_container_exists(ui_files):
    assert 'id="opp-detail-actions"' in ui_files["html"]


def test_metadata_source_label_exists(ui_files):
    """Verify 'Fonte' label is present in metadata."""
    assert "<dt>Fonte</dt>" in ui_files["html"]


def test_metadata_captured_at_label_exists(ui_files):
    """Verify 'Capturada em' label is present in metadata."""
    assert "<dt>Capturada em</dt>" in ui_files["html"]


def test_metadata_triage_note_label_exists(ui_files):
    """Verify 'Nota de triagem' label is present in metadata."""
    assert "<dt>Nota de triagem</dt>" in ui_files["html"]


# --- JavaScript behavior ---


def test_select_opportunity_populates_source(ui_files):
    """selectOpportunity must populate selected-source."""
    assert 'selected-source' in ui_files["js"]
    assert "record.source" in ui_files["js"]


def test_select_opportunity_populates_captured_at(ui_files):
    """selectOpportunity must populate selected-captured-at."""
    assert 'selected-captured-at' in ui_files["js"]
    assert "captured_at" in ui_files["js"]


def test_select_opportunity_populates_triage_note(ui_files):
    """selectOpportunity must populate selected-triage-note."""
    assert 'selected-triage-note' in ui_files["js"]
    assert "triage_note" in ui_files["js"]


def test_select_opportunity_always_loads_brief(ui_files):
    """selectOpportunity must always call loadBrief, regardless of status.

    The old code had:
        if (record.next_action === "prepare_proposal") {
            await loadBrief(id, version);
        } else { ... }

    WP-108 removes the conditional and always loads the brief.
    """
    # The function should contain loadBrief call
    assert "await loadBrief(id, version)" in ui_files["js"]
    # The old conditional should NOT exist
    assert 'record.next_action === "prepare_proposal"' not in ui_files["js"]


def test_view_brief_button_handler_exists(ui_files):
    """The view-brief-button click handler must scroll to brief-panel."""
    assert 'view-brief-button' in ui_files["js"]
    assert "scrollIntoView" in ui_files["js"]


def test_clear_selection_clears_new_fields(ui_files):
    """clearSelection must clear the new metadata fields."""
    # Check that clearSelection includes the new field IDs
    js = ui_files["js"]
    # Find the clearSelection function
    assert "selected-source" in js
    assert "selected-captured-at" in js
    assert "selected-triage-note" in js


# --- CSS styles ---


def test_opp_detail_actions_css_exists(ui_files):
    assert ".opp-detail-actions" in ui_files["css"]


def test_opp_detail_actions_button_css_exists(ui_files):
    assert ".opp-detail-actions button" in ui_files["css"]


# --- Integration: metadata order ---


def test_metadata_order_in_html(ui_files):
    """Verify metadata fields appear in logical order: source, url, budget, deadline, requirements, captured_at, triage_note."""
    html = ui_files["html"]
    # Find the metadata dl section
    meta_start = html.index('<dl class="metadata">')
    # Find the end (next </dl> or the triage form)
    meta_end = html.index('id="triage-form"', meta_start)
    metadata_section = html[meta_start:meta_end]

    # Check order
    source_pos = metadata_section.index('id="selected-source"')
    url_pos = metadata_section.index('id="selected-url"')
    budget_pos = metadata_section.index('id="selected-budget"')
    deadline_pos = metadata_section.index('id="selected-deadline"')
    requirements_pos = metadata_section.index('id="selected-requirements"')
    captured_pos = metadata_section.index('id="selected-captured-at"')
    triage_note_pos = metadata_section.index('id="selected-triage-note"')

    assert source_pos < url_pos < budget_pos < deadline_pos < requirements_pos < captured_pos < triage_note_pos


def test_view_brief_button_in_metadata_section(ui_files):
    """The view-brief-button should be between metadata and triage form."""
    html = ui_files["html"]
    meta_start = html.index('<dl class="metadata">')
    triage_start = html.index('id="triage-form"', meta_start)
    between = html[meta_start:triage_start]
    assert 'id="view-brief-button"' in between

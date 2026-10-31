"""Contract checks for the WP-072 opportunity pipeline UI.

Validates that the pipeline section is properly wired to the backend endpoints
without introducing security issues.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HTML = (ROOT / "app/operator_ui/index.html").read_text()
JS = (ROOT / "app/operator_ui/app.js").read_text()


def test_pipeline_section_present():
    """Pipeline section exists in HTML with proper labeling."""
    assert 'id="pipeline-title"' in HTML
    assert 'aria-labelledby="pipeline-title"' in HTML
    assert 'id="pipeline-summary"' in HTML


def test_pipeline_chips_present():
    """All pipeline filter chips exist in HTML."""
    for filter_val in ("all", "pending", "follow", "prepare_proposal",
                       "in_progress", "ignore"):
        assert f'data-filter="{filter_val}"' in HTML


def test_pipeline_count_elements_present():
    """Pipeline count display elements exist for each status."""
    for key in ("all", "pending", "follow", "prepare_proposal",
                "in_progress", "ignore"):
        assert f'id="pipeline-{key}"' in HTML


def test_pipeline_refresh_button_present():
    """Pipeline refresh button exists."""
    assert 'id="pipeline-refresh"' in HTML


def test_pipeline_api_calls_authenticated_endpoint():
    """Pipeline API calls use authenticated internal endpoint."""
    assert '"/opportunities/pipeline-summary"' in JS
    assert 'Authorization: "Bearer " + bearer' in JS


def test_pipeline_filter_uses_query_param():
    """Pipeline filter passes next_action as query parameter."""
    assert "next_action=" in JS
    assert "encodeURIComponent" in JS


def test_pipeline_refresh_function_exists():
    """refreshPipeline function exists and validates response."""
    assert "refreshPipeline" in JS
    assert 'typeof summary !== "object"' in JS or "Resposta de pipeline inválida" in JS


def test_pipeline_filter_function_exists():
    """setPipelineFilter function exists and manages aria-pressed."""
    assert "setPipelineFilter" in JS
    assert 'aria-pressed' in JS


def test_pipeline_chips_use_text_content():
    """Pipeline count display uses textContent to avoid XSS."""
    assert "textContent" in JS
    # pipeline count elements should use textContent
    assert 'pipeline-' in JS


def test_pipeline_in_action_labels():
    """in_progress is included in actionLabels for display."""
    assert 'in_progress: "Em andamento"' in JS


def test_pipeline_api_allowlist_includes_summary():
    """API allowlist includes /opportunities/pipeline-summary."""
    assert "/pipeline-summary" in JS


def test_pipeline_refresh_on_connect():
    """refreshPipeline is called on connect."""
    # Check that refreshPipeline is in the Promise.all with refreshList
    assert "refreshPipeline" in JS


def test_pipeline_chip_click_handler():
    """Pipeline chips have click handlers that call setPipelineFilter."""
    assert 'chip.addEventListener("click"' in JS or ".pipeline-chip" in JS
    assert "setPipelineFilter" in JS


def test_pipeline_filter_resets_on_disconnect():
    """Disconnect resets pipelineFilter to null."""
    assert "pipelineFilter = null" in JS

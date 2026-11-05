"""UI operativa: endpoints estáticos, bloqueio de rede e auth de domínio."""

from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app


def test_operator_page_is_static_local_and_never_embeds_credentials(client):
    response = client.get("/operator")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Business Automation" in response.text
    assert 'id="workspace" hidden' in response.text
    assert 'id="operator-token"' in response.text
    assert 'src="/operator/app.js"' in response.text
    assert 'href="/operator/styles.css"' in response.text
    assert "<script>" not in response.text
    assert "<style>" not in response.text
    assert "test-operator-a-token" not in response.text
    assert "BA_ACCESS_IDENTITIES_JSON" not in response.text

    for key in ("Cache-Control", "Content-Security-Policy", "X-Frame-Options"):
        assert key in response.headers
    assert response.headers["cache-control"] == "no-store"
    csp = response.headers["content-security-policy"]
    assert "default-src 'none'" in csp
    assert "script-src 'self'" in csp
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "'unsafe-inline'" not in csp
    assert "http" not in csp
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cross-origin-resource-policy"] == "same-origin"


def test_operator_assets_are_fixed_read_only_and_private_cache(client):
    script = client.get("/operator/app.js")
    styles = client.get("/operator/styles.css")
    assert script.status_code == 200
    assert styles.status_code == 200
    assert "text/javascript" in script.headers["content-type"]
    assert "text/css" in styles.headers["content-type"]
    for response in (script, styles):
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-content-type-options"] == "nosniff"
        assert response.headers["content-security-policy"].startswith("default-src 'none'")

    assert "Authorization" in script.text
    assert 'credentials: "omit"' in script.text
    assert 'redirect: "error"' in script.text
    assert ".textContent" in script.text
    assert "if (epoch !== sessionEpoch)" in script.text
    assert 'window.addEventListener("pagehide"' in script.text
    assert '$("triage-form").reset()' in script.text
    assert '$(id).textContent = ""' in script.text
    assert 'new Date().toISOString()' in script.text
    assert 'source: fields.source' in script.text
    assert '/proposal-brief' in script.text

    # WP-163: localStorage is allowed ONLY for theme preference ("operator-theme")
    # Verify no sensitive data is persisted
    assert "sessionStorage" not in script.text
    assert "document.cookie" not in script.text
    assert "innerHTML" not in script.text
    assert "insertAdjacentHTML" not in script.text
    assert "console.log" not in script.text
    assert "eval(" not in script.text
    assert "window.open" not in script.text
    # localStorage is only used for theme, not for bearer tokens or secrets
    if "localStorage" in script.text:
        assert 'setItem("operator-theme"' in script.text
        assert 'getItem("operator-theme")' in script.text
        # Ensure bearer token is NOT in localStorage
        assert 'setItem("bearer"' not in script.text
        assert 'setItem("token"' not in script.text


def test_ui_is_not_an_authentication_bypass(
    client,
    admin_headers,
    operator_a_headers,
):
    assert client.get("/operator").status_code == 200
    assert client.get("/opportunities").status_code == 401
    assert client.post("/opportunities", json={}).status_code == 401
    assert client.get("/opportunities", headers=admin_headers).status_code == 403
    assert client.get("/opportunities", headers=operator_a_headers).status_code == 200
    assert client.post("/operator").status_code == 405
    assert client.post("/operator/app.js").status_code == 405
    assert "/operator" not in client.get("/openapi.json").json()["paths"]


def test_operator_ui_rejects_remote_client_and_nonlocal_host():
    with TestClient(
        app, base_url="http://localhost", client=("198.51.100.23", 54321)
    ) as remote:
        for route in ("/operator", "/operator/app.js", "/operator/styles.css"):
            assert remote.get(route).status_code == 404

    with TestClient(app, base_url="http://attacker.example") as spoofed_host:
        assert spoofed_host.get("/operator").status_code == 404

    with TestClient(
        app, base_url="http://localhost", client=("127.0.0.1", 54321)
    ) as local:
        assert local.get("/operator").status_code == 200
        assert local.get("/operator/app.js").status_code == 200


def test_client0_form_has_all_required_fields_without_price_or_submission(client):
    page = client.get("/operator").text
    for required in (
        'name="title"', 'name="external_url"', 'name="description"',
        'name="requirements"', 'name="budget"', 'name="deadline"',
        'name="next_action"', 'name="triage_note"',
        'name="offer_reference"', 'name="diagnosis"', 'name="scope"',
        'name="deliverables"', 'name="acceptance_criteria"',
        'name="assumptions"', 'name="risks"', 'name="status"',
    ):
        assert required in page
    assert 'value="ready_for_review"' in page
    # WP-071/084: approval uses dedicated buttons, not a select option
    assert 'id="brief-approve"' in page
    assert 'id="brief-reject"' in page
    assert 'name="price"' not in page
    assert 'name="company_id"' not in page

    # A UI não pode receber paths dinâmicos/estáticos arbitrários.
    for invalid in ("/operator/data.json", "/operator/test.env", "/operator/debug"):
        assert client.get(invalid).status_code == 404
def test_brief_status_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="brief-status"' in html
    assert 'aria-live="polite"' in html


def test_task_failure_badge_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="task-failed-badge" class="pending-badge" hidden aria-live="polite"' in html


def test_task_list_has_list_semantics():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="tasks-list" class="task-list" role="list" aria-label="Lista de tarefas internas"' in html


def test_task_bulk_selection_count_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="task-bulk-selected-count" class="small" aria-live="polite"' in html


def test_opportunity_bulk_actions_have_context_label():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="bulk-triage-bar" class="bulk-triage-bar" role="group" aria-label="Ações de triagem em massa" hidden' in html


def test_opportunity_bulk_selection_count_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="bulk-selected-count" class="small" aria-live="polite"' in html


def test_opportunity_list_items_have_listitem_semantics():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'wrapper.setAttribute("role", "listitem")' in js


def test_opportunity_list_has_list_semantics():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="opportunity-list" class="opportunity-list" role="list" aria-label="Lista de oportunidades"' in html


def test_opportunity_current_page_has_current_semantics():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="opp-page" class="small" aria-live="polite" aria-current="page"' in html


def test_task_export_controls_task_list():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="tasks-export-csv" type="button" class="secondary" aria-controls="tasks-list">Exportar CSV' in html


def test_task_clear_filters_controls_task_list():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="task-clear-filters" type="button" class="secondary" aria-controls="tasks-list">Limpar filtros' in html


def test_task_failure_badge_has_accessible_label():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="task-failed-badge" class="pending-badge" hidden aria-live="polite" aria-label="Tarefas falhas"' in html


def test_task_refresh_controls_task_list():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="tasks-refresh" type="button" aria-controls="tasks-list">Atualizar' in html


def test_task_list_exposes_loading_state():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'taskList.setAttribute("aria-busy", "true")' in js
    assert 'taskList.setAttribute("aria-busy", "false")' in js


def test_empty_task_state_is_status_region():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'empty.setAttribute("role", "status")' in js


def test_task_bulk_actions_have_context_label():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="task-bulk-bar" class="task-bulk-bar" role="group" aria-label="Ações de tarefas em massa" hidden' in html


def test_task_bulk_retry_uses_accessible_portuguese_label():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="task-bulk-retry" type="button" class="primary" aria-label="Tentar novamente as tarefas selecionadas">Tentar novamente selecionadas' in html


def test_task_error_messages_are_alerts():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'err.setAttribute("role", "alert")' in js


def test_task_retry_buttons_use_portuguese_label():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'retryBtn.textContent = "Tentar novamente"' in js


def test_task_retry_buttons_have_accessible_labels():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'retryBtn.setAttribute("aria-label", "Tentar novamente a tarefa #" + task.id)' in js


def test_task_selection_checkboxes_have_accessible_labels():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'checkbox.setAttribute("aria-label", "Selecionar tarefa #" + task.id)' in js


def test_task_list_items_have_listitem_semantics():
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'item.setAttribute("role", "listitem")' in js


def test_task_pagination_status_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="tasks-page-info" class="small" aria-live="polite"' in html


def test_task_pagination_has_navigation_semantics():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="tasks-pagination" class="task-pagination" role="navigation" aria-label="Paginação de tarefas" hidden' in html


def test_opportunity_pagination_controls_have_context_labels():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="opp-prev" type="button" class="secondary" aria-label="Página anterior de oportunidades" disabled' in html
    assert 'id="opp-next" type="button" class="secondary" aria-label="Próxima página de oportunidades" disabled' in html


def test_opportunity_pagination_has_navigation_semantics():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="opp-pagination" class="opp-pagination" role="navigation" aria-label="Paginação de oportunidades" hidden' in html


def test_opportunity_pagination_status_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="opp-page" class="small" aria-live="polite"' in html


def test_opportunity_list_summary_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="list-meta" class="small" aria-live="polite"' in html


def test_opportunity_edit_group_has_accessible_name():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="opp-edit-panel" class="opp-edit-panel" role="group" aria-labelledby="opp-edit-title"' in html
    assert '<h3 id="opp-edit-title">Editar oportunidade</h3>' in html


def test_opportunity_progress_bar_describes_visible_percent():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'aria-describedby="opp-progress-percent"' in html


def test_selected_opportunity_id_has_context_label():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="selected-id" class="tag" aria-label="Oportunidade selecionada" aria-live="polite"' in html


def test_opportunity_progress_bar_has_accessible_semantics():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    js = (Path(__file__).parents[1] / "app/operator_ui/app.js").read_text()
    assert 'id="opp-progress-fill"' in html
    assert 'role="progressbar"' in html
    assert 'aria-valuemin="0"' in html
    assert 'aria-valuemax="100"' in html
    assert 'aria-valuenow="0"' in html
    assert 'setAttribute("aria-valuenow", String(percent))' in js


def test_opportunity_progress_percent_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="opp-progress-percent" class="small" aria-live="polite"' in html


def test_selected_opportunity_captured_at_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="selected-captured-at" aria-live="polite"' in html


def test_selected_opportunity_requirements_are_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="selected-requirements" class="break-word" aria-live="polite"' in html


def test_selected_opportunity_deadline_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="selected-deadline" aria-live="polite"' in html


def test_selected_opportunity_budget_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="selected-budget" aria-live="polite"' in html


def test_selected_opportunity_origin_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="selected-url" class="break-word" aria-live="polite"' in html


def test_triage_note_is_live_region():
    html = (Path(__file__).parents[1] / "app/operator_ui/index.html").read_text()
    assert 'id="selected-triage-note"' in html
    assert 'aria-live="polite"' in html

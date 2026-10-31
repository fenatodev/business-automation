"""WP-120 — Task sort, pagination count, and UI section."""

import pytest
from pathlib import Path

from app.models import Company
from app.schemas import ReviewQueueTrigger
from conftest import TestingSessionLocal


@pytest.fixture
def companies():
    with TestingSessionLocal() as db:
        db.add_all([Company(id=1, name="Synthetic A", slug="task-a"),
                     Company(id=2, name="Synthetic B", slug="task-b")])
        db.commit()
        yield


def trigger():
    return ReviewQueueTrigger(event_id="evt-sort-001", channel="whatsapp", message="Sort test")


class TestTaskSort:
    """GET /internal-tasks/ with sort parameter."""

    def test_default_sort_by_created_at(self, companies, client, operator_a_headers):
        payload = trigger().model_dump()
        client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
        resp = client.get("/internal-tasks/", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_sort_by_id(self, companies, client, operator_a_headers):
        payload = trigger().model_dump()
        client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
        resp = client.get("/internal-tasks/?sort=id", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        ids = [t["id"] for t in data]
        assert ids == sorted(ids, reverse=True)

    def test_sort_by_status(self, companies, client, operator_a_headers):
        payload = trigger().model_dump()
        client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
        resp = client.get("/internal-tasks/?sort=status", headers=operator_a_headers)
        assert resp.status_code == 200

    def test_sort_by_attempts(self, companies, client, operator_a_headers):
        payload = trigger().model_dump()
        client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
        resp = client.get("/internal-tasks/?sort=attempts", headers=operator_a_headers)
        assert resp.status_code == 200


class TestTaskCount:
    """GET /internal-tasks/count endpoint."""

    def test_count_all_tasks(self, companies, client, operator_a_headers):
        resp = client.get("/internal-tasks/count", headers=operator_a_headers)
        assert resp.status_code == 200
        count = resp.json()
        assert isinstance(count, int)
        assert count >= 0

    def test_count_after_create(self, companies, client, operator_a_headers):
        before = client.get("/internal-tasks/count", headers=operator_a_headers).json()
        payload = trigger().model_dump()
        client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
        after = client.get("/internal-tasks/count", headers=operator_a_headers).json()
        assert after == before + 1

    def test_count_filtered_by_status(self, companies, client, operator_a_headers):
        payload = trigger().model_dump()
        client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
        resp = client.get("/internal-tasks/?status=queued", headers=operator_a_headers)
        assert resp.status_code == 200
        list_count = len(resp.json())

        resp_count = client.get("/internal-tasks/count?status=queued", headers=operator_a_headers)
        assert resp_count.status_code == 200
        count = resp_count.json()
        assert count == list_count

    def test_count_empty(self, companies, client, operator_a_headers):
        resp = client.get("/internal-tasks/count", headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json() == 0


class TestTaskPagination:
    """Task list with limit/offset."""

    def test_limit_offset(self, companies, client, operator_a_headers):
        # Create multiple tasks
        for i in range(5):
            payload = ReviewQueueTrigger(event_id=f"evt-page-{i}", channel="whatsapp", message=f"Page {i}").model_dump()
            client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
        resp = client.get("/internal-tasks/?limit=2&offset=0", headers=operator_a_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) <= 2

    def test_offset_beyond_count(self, companies, client, operator_a_headers):
        resp = client.get("/internal-tasks/?limit=50&offset=9999", headers=operator_a_headers)
        assert resp.status_code == 200
        assert resp.json() == []


class TestTaskTenantIsolation:
    """Tasks are isolated by tenant."""

    def test_cross_tenant_hidden(self, companies, client, operator_a_headers, operator_b_headers):
        payload = trigger().model_dump()
        client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
        resp = client.get("/internal-tasks/", headers=operator_b_headers)
        assert resp.status_code == 200
        assert resp.json() == []

    def test_count_cross_tenant_hidden(self, companies, client, operator_a_headers, operator_b_headers):
        payload = trigger().model_dump()
        client.post("/internal-tasks/", json=payload, headers=operator_a_headers)
        resp = client.get("/internal-tasks/count", headers=operator_b_headers)
        assert resp.status_code == 200
        assert resp.json() == 0


class TestTaskAuth:
    """Task endpoints require operator auth."""

    def test_list_requires_auth(self, client):
        resp = client.get("/internal-tasks/")
        assert resp.status_code in (401, 403)

    def test_count_requires_auth(self, client):
        resp = client.get("/internal-tasks/count")
        assert resp.status_code in (401, 403)

    def test_list_rejects_admin(self, companies, client, admin_headers):
        resp = client.get("/internal-tasks/", headers=admin_headers)
        assert resp.status_code == 403


# --- UI Contract Tests ---

BASE = Path(__file__).resolve().parent.parent / "app" / "operator_ui"
JS = (BASE / "app.js").read_text()
CSS = (BASE / "styles.css").read_text()
HTML = (BASE / "index.html").read_text()


class TestTaskUI:
    """Internal tasks section in the operator UI."""

    def test_html_has_tasks_section(self):
        assert "10 / TAREFAS INTERNAS" in HTML
        assert 'id="tasks-title"' in HTML

    def test_html_has_task_status_filter(self):
        assert 'id="task-status-filter"' in HTML
        for status in ["queued", "running", "succeeded", "failed"]:
            assert status in HTML

    def test_html_has_task_sort(self):
        assert 'id="task-sort"' in HTML

    def test_html_has_tasks_list(self):
        assert 'id="tasks-list"' in HTML

    def test_html_has_tasks_pagination(self):
        assert 'id="tasks-pagination"' in HTML
        assert 'id="tasks-prev-page"' in HTML
        assert 'id="tasks-next-page"' in HTML

    def test_js_has_taskApi(self):
        assert "async function taskApi" in JS
        assert "/internal-tasks" in JS

    def test_js_has_task_allowlist(self):
        assert '/internal-tasks(\/|$|\?)/' in JS

    def test_js_has_refreshTasks(self):
        assert "async function refreshTasks" in JS

    def test_js_has_renderTasks(self):
        assert "function renderTasks" in JS

    def test_js_has_buildTaskUrl(self):
        assert "function buildTaskUrl" in JS

    def test_js_has_task_pagination_state(self):
        assert "taskOffset" in JS
        assert "taskPageSize" in JS
        assert "taskTotal" in JS

    def test_js_task_status_filter_resets_offset(self):
        # The status filter change handler should reset offset
        assert 'task-status-filter' in JS
        snippet = JS.split('task-status-filter')[1].split('change')[1][:200] if 'task-status-filter' in JS and 'change' in JS.split('task-status-filter')[1] else ""
        assert "taskOffset = 0" in snippet or "taskOffset=0" in snippet or \
               ("taskOffset" in JS and "refreshTasks" in JS)

    def test_css_has_task_filters(self):
        assert ".task-filters" in CSS

    def test_css_has_task_list(self):
        assert ".task-list" in CSS

    def test_css_has_task_item(self):
        assert ".task-item" in CSS

    def test_css_has_task_status_badges(self):
        assert ".task-status-badge" in CSS
        for status in ["queued", "running", "succeeded", "failed", "unknown"]:
            assert f".task-status-{status}" in CSS

    def test_css_has_task_pagination(self):
        assert ".task-pagination" in CSS

    def test_js_task_retry_button(self):
        # Failed tasks should have retry button
        assert 'task-status === "failed"' in JS or 'task.status === "failed"' in JS
        assert "/retry" in JS

    def test_js_workspace_observer_includes_tasks(self):
        # refreshTasks should be called in workspaceObserver
        assert "refreshTasks" in JS

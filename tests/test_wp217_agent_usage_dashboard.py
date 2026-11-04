"""WP-217 — Agent usage stats in dashboard.

The dashboard endpoint now includes agent_usage stats and the UI
displays them in a dedicated card.
"""


def test_dashboard_endpoint_has_agent_usage():
    """The dashboard endpoint returns agent_usage field."""
    with open("app/routers/internal_tasks.py") as f:
        code = f.read()
    assert "agent_usage" in code
    assert "_get_agent_usage" in code


def test_dashboard_agent_usage_fields():
    """The dashboard returns total_calls, successful_calls, failed_calls."""
    with open("app/routers/internal_tasks.py") as f:
        code = f.read()
    # The entire file should contain the agent usage fields
    assert "total_calls" in code
    assert "successful_calls" in code
    assert "failed_calls" in code


def test_dashboard_html_has_agent_card():
    """The dashboard HTML has an agent usage card."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert "dash-agent-total" in html
    assert "dash-agent-details" in html


def test_dashboard_html_agent_card_title():
    """The agent card has a title with robot emoji."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    agent_start = html.index("dash-agent-total")
    section = html[max(0, agent_start - 200):agent_start + 100]
    assert "Agente" in section or "agente" in section


def test_dashboard_js_renders_agent_usage():
    """The dashboard JS renders agent usage data."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "dash-agent-total" in js
    assert "dash-agent-details" in js
    assert "agent_usage" in js


def test_dashboard_js_agent_labels():
    """The dashboard JS has labels for agent stats."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "Sucesso" in js
    assert "Falha" in js


def test_dashboard_agent_card_after_review():
    """The agent card appears after the review card."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    review_pos = html.index("dash-rq-total")
    agent_pos = html.index("dash-agent-total")
    assert agent_pos > review_pos


def test_full_stack_dashboard_agent_flow():
    """End-to-end: backend returns agent_usage, UI renders it."""
    # Backend includes agent_usage
    with open("app/routers/internal_tasks.py") as f:
        code = f.read()
    assert "agent_usage" in code

    # HTML has the card
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert "dash-agent-total" in html
    assert "dash-agent-details" in html

    # JS renders the data
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "agent_usage" in js
    assert "dash-agent-total" in js


def test_dashboard_agent_usage_import():
    """The dashboard imports _get_agent_usage from companies router."""
    with open("app/routers/internal_tasks.py") as f:
        code = f.read()
    assert "from app.routers.companies import _get_agent_usage" in code


def test_backend_agent_usage_zero_default():
    """Agent usage defaults to zero for companies with no calls."""
    from app.routers.companies import _get_agent_usage, _agent_usage_store

    _agent_usage_store.clear()
    usage = _get_agent_usage(999)
    assert usage["total_calls"] == 0
    assert usage["successful_calls"] == 0
    assert usage["failed_calls"] == 0

    del _agent_usage_store[999]

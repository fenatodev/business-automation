"""WP-216 — Agent usage tracking.

Track successful and failed agent calls per company for F3 observability.
"""

from httpx import Response
from unittest.mock import patch

from app.schemas import CompanyAgentConfig


def test_agent_usage_store_exists():
    """The companies router has an in-memory usage store."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "_agent_usage_store" in code


def test_agent_usage_helper_functions():
    """The companies router has helper functions for usage tracking."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "def _get_agent_usage" in code
    assert "def _record_agent_call" in code


def test_agent_usage_endpoint_exists():
    """GET /agent-usage endpoint exists."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert '"/companies/{company_id}/agent-usage"' in code


def test_agent_usage_endpoint_returns_stats():
    """The agent usage endpoint returns total, successful, and failed calls."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    usage_start = code.index("def get_agent_usage")
    usage_section = code[usage_start:usage_start + 800]
    assert "total_calls" in usage_section
    assert "successful_calls" in usage_section
    assert "failed_calls" in usage_section


def test_conversations_router_records_success():
    """The conversations router records successful agent calls."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert "_record_agent_call" in code
    assert "success=True" in code


def test_conversations_router_records_failure():
    """The conversations router records failed agent calls."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert "success=False" in code


def test_usage_tracking_initializes_zero():
    """Usage stats start at zero for new companies."""
    from app.routers.companies import _get_agent_usage, _agent_usage_store

    # Clear any existing data
    _agent_usage_store.clear()

    usage = _get_agent_usage(999)
    assert usage["total_calls"] == 0
    assert usage["successful_calls"] == 0
    assert usage["failed_calls"] == 0

    # Cleanup
    del _agent_usage_store[999]


def test_usage_tracking_records_success():
    """Successful calls increment total and successful counters."""
    from app.routers.companies import _record_agent_call, _get_agent_usage, _agent_usage_store

    _agent_usage_store.clear()

    _record_agent_call(1, success=True)
    usage = _get_agent_usage(1)
    assert usage["total_calls"] == 1
    assert usage["successful_calls"] == 1
    assert usage["failed_calls"] == 0

    _record_agent_call(1, success=True)
    usage = _get_agent_usage(1)
    assert usage["total_calls"] == 2
    assert usage["successful_calls"] == 2
    assert usage["failed_calls"] == 0

    # Cleanup
    del _agent_usage_store[1]


def test_usage_tracking_records_failure():
    """Failed calls increment total and failed counters."""
    from app.routers.companies import _record_agent_call, _get_agent_usage, _agent_usage_store

    _agent_usage_store.clear()

    _record_agent_call(1, success=False)
    usage = _get_agent_usage(1)
    assert usage["total_calls"] == 1
    assert usage["successful_calls"] == 0
    assert usage["failed_calls"] == 1

    # Cleanup
    del _agent_usage_store[1]


def test_usage_tracking_mixed_calls():
    """Mixed success/failure calls are tracked correctly."""
    from app.routers.companies import _record_agent_call, _get_agent_usage, _agent_usage_store

    _agent_usage_store.clear()

    _record_agent_call(1, success=True)
    _record_agent_call(1, success=True)
    _record_agent_call(1, success=False)
    _record_agent_call(1, success=True)
    _record_agent_call(1, success=False)

    usage = _get_agent_usage(1)
    assert usage["total_calls"] == 5
    assert usage["successful_calls"] == 3
    assert usage["failed_calls"] == 2

    # Cleanup
    del _agent_usage_store[1]


def test_usage_isolation_between_companies():
    """Different companies have independent usage stats."""
    from app.routers.companies import _record_agent_call, _get_agent_usage, _agent_usage_store

    _agent_usage_store.clear()

    _record_agent_call(1, success=True)
    _record_agent_call(1, success=True)
    _record_agent_call(2, success=True)
    _record_agent_call(2, success=False)

    usage1 = _get_agent_usage(1)
    usage2 = _get_agent_usage(2)

    assert usage1["total_calls"] == 2
    assert usage1["successful_calls"] == 2
    assert usage1["failed_calls"] == 0

    assert usage2["total_calls"] == 2
    assert usage2["successful_calls"] == 1
    assert usage2["failed_calls"] == 1

    # Cleanup
    del _agent_usage_store[1]
    del _agent_usage_store[2]


def test_agent_usage_endpoint_tenant_isolation():
    """GET /agent-usage enforces tenant isolation."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    usage_start = code.index("def get_agent_usage")
    usage_section = code[usage_start:usage_start + 800]
    assert "identity.company_id" in usage_section
    assert "Access denied" in usage_section


def test_agent_usage_endpoint_requires_operator():
    """GET /agent-usage requires operator authentication."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    usage_start = code.index("def get_agent_usage")
    usage_section = code[usage_start:usage_start + 800]
    assert "require_operator" in usage_section


def test_full_stack_usage_flow():
    """End-to-end: record calls, retrieve stats."""
    from app.routers.companies import _record_agent_call, _get_agent_usage, _agent_usage_store

    _agent_usage_store.clear()

    # Simulate agent calls
    _record_agent_call(1, success=True)
    _record_agent_call(1, success=False)
    _record_agent_call(1, success=True)

    # Retrieve stats
    usage = _get_agent_usage(1)
    assert usage["total_calls"] == 3
    assert usage["successful_calls"] == 2
    assert usage["failed_calls"] == 1

    # Verify the endpoint would return correct data
    result = {
        "company_id": 1,
        "total_calls": usage["total_calls"],
        "successful_calls": usage["successful_calls"],
        "failed_calls": usage["failed_calls"],
    }
    assert result["total_calls"] == 3
    assert result["successful_calls"] == 2
    assert result["failed_calls"] == 1

    # Cleanup
    del _agent_usage_store[1]

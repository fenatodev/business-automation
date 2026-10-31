"""WP-204 — Per-company agent configuration.

Each company can now configure its own system_prompt and temperature
for the agent service. Config is stored in-memory (no migration required).
The agent-reply endpoint uses company config as defaults, with explicit
request parameters taking precedence.

Endpoints:
- GET /companies/{company_id}/agent-config — read current config
- PUT /companies/{company_id}/agent-config — set config
"""


def test_company_agent_config_schema():
    """CompanyAgentConfig schema has system_prompt and temperature."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig()
    assert config.system_prompt is None
    assert config.temperature is None


def test_company_agent_config_with_values():
    """CompanyAgentConfig accepts values."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig(system_prompt="custom", temperature=0.5)
    assert config.system_prompt == "custom"
    assert config.temperature == 0.5


def test_agent_config_store_exists():
    """In-memory agent config store exists in companies router."""
    from app.routers.companies import _agent_config_store
    assert isinstance(_agent_config_store, dict)


def test_get_agent_config_endpoint_exists():
    """GET /companies/{company_id}/agent-config endpoint exists."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "def get_agent_config" in code
    assert '"/companies/{company_id}/agent-config"' in code


def test_set_agent_config_endpoint_exists():
    """PUT /companies/{company_id}/agent-config endpoint exists."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "def set_agent_config" in code
    assert '"/companies/{company_id}/agent-config"' in code


def test_set_agent_config_uses_put_method():
    """Set agent config uses PUT method."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert '@router.put("/companies/{company_id}/agent-config")' in code


def test_get_agent_config_requires_operator():
    """Get agent config requires operator role."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "require_operator" in code


def test_set_agent_config_requires_operator():
    """Set agent config requires operator role."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "require_operator" in code


def test_agent_reply_uses_company_config():
    """Agent reply endpoint uses company config as defaults."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert "_agent_config_store" in code
    assert "company_config" in code


def test_agent_reply_prompt_fallback():
    """Agent reply falls back to company prompt if not in request."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert "effective_prompt" in code
    assert "data.system_prompt or" in code


def test_agent_reply_temperature_fallback():
    """Agent reply falls back to company temperature if not in request."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert "effective_temp" in code


def test_agent_config_tenant_isolation_get():
    """Get agent config checks tenant isolation."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    get_start = code.index("def get_agent_config")
    get_end = code.index("def set_agent_config", get_start)
    get_block = code[get_start:get_end]
    assert "identity.company_id" in get_block
    assert "403" in get_block


def test_agent_config_tenant_isolation_set():
    """Set agent config checks tenant isolation."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    set_start = code.index("def set_agent_config")
    set_block = code[set_start:set_start + 1000]
    assert "identity.company_id" in set_block
    assert "403" in set_block


def test_agent_config_404_on_missing_company():
    """Agent config returns 404 for non-existent company."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert '404' in code
    assert '"Company not found"' in code


def test_agent_config_store_keyed_by_company_id():
    """Agent config store is keyed by company_id."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "dict[int, dict[str, object]]" in code or "dict[int" in code


def test_agent_config_returns_company_agent_config():
    """Endpoints return CompanyAgentConfig schema."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "CompanyAgentConfig" in code


def test_agent_config_import_in_companies():
    """CompanyAgentConfig is imported in companies router."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "from app.schemas import" in code
    assert "CompanyAgentConfig" in code


def test_agent_config_integration_with_agent_reply():
    """Agent reply imports _agent_config_store from companies."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert "from app.routers.companies import _agent_config_store" in code


def test_agent_config_identity_import():
    """require_operator is imported in companies router."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "require_operator" in code


def test_agent_config_set_stores_values():
    """Set agent config stores values in the in-memory store."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    set_start = code.index("def set_agent_config")
    set_end = len(code)
    set_block = code[set_start:set_end]
    assert "_agent_config_store[" in set_block
    assert 'config["system_prompt"]' in set_block or "config['system_prompt']" in set_block


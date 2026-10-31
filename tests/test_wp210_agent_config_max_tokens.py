"""WP-210 — Max tokens field in agent config UI.

The agent config UI had system_prompt and temperature fields but was
missing max_tokens (added in WP-208). This test verifies the UI contract.
"""


def test_agent_config_has_max_tokens_field():
    """The agent config form has a max_tokens input field."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="agent-max-tokens"' in html


def test_agent_config_max_tokens_is_number_input():
    """The max_tokens field is a number input."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    # Find the input tag containing agent-max-tokens
    start = html.index('id="agent-max-tokens"')
    # Look backwards for the opening tag
    tag_start = html.rindex('<', 0, start)
    tag_end = html.index('>', start)
    tag = html[tag_start:tag_end+1]
    assert 'type="number"' in tag


def test_agent_config_max_tokens_has_min_attribute():
    """The max_tokens field has min=1 to prevent invalid values."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="agent-max-tokens"')
    field = html[start:start+200]
    assert 'min="1"' in field


def test_agent_config_max_tokens_has_placeholder():
    """The max_tokens field has a helpful placeholder."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="agent-max-tokens"')
    field = html[start:start+300]
    assert 'placeholder=' in field


def test_agent_config_max_tokens_after_temperature():
    """The max_tokens field appears after temperature in the form."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    temp_pos = html.index('id="agent-temperature"')
    max_tokens_pos = html.index('id="agent-max-tokens"')
    assert max_tokens_pos > temp_pos


def test_agent_config_max_tokens_before_status():
    """The max_tokens field appears before the status message."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    max_tokens_pos = html.index('id="agent-max-tokens"')
    status_pos = html.index('id="agent-config-status"')
    assert max_tokens_pos < status_pos


def test_app_js_loads_max_tokens():
    """app.js loadAgentConfig reads max_tokens from API response."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert 'agent-max-tokens' in js
    assert 'res.max_tokens' in js


def test_app_js_saves_max_tokens():
    """app.js save handler includes max_tokens in request body."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    # Find the save handler
    save_start = js.index('agent-config-save')
    save_section = js[save_start:save_start+500]
    assert 'max_tokens' in save_section
    assert 'parseInt' in save_section


def test_app_js_max_tokens_parsing():
    """max_tokens is parsed as integer, not float."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    save_start = js.index('agent-config-save')
    save_section = js[save_start:save_start+500]
    assert 'parseInt(maxTokens' in save_section


def test_app_js_max_tokens_empty_check():
    """max_tokens is only saved when non-empty."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    save_start = js.index('agent-config-save')
    save_section = js[save_start:save_start+500]
    assert 'maxTokens !== ""' in save_section


def test_agent_config_form_structure():
    """The agent config form has all three fields: prompt, temperature, max_tokens."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    form_start = html.index('class="agent-config-form"')
    form_end = html.index('</section>', form_start)
    form = html[form_start:form_end]
    assert 'id="agent-system-prompt"' in form
    assert 'id="agent-temperature"' in form
    assert 'id="agent-max-tokens"' in form


def test_agent_config_max_tokens_label():
    """The max_tokens field has a label."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="agent-max-tokens"')
    # Look backwards for the label
    before = html[max(0, start-200):start]
    assert '<label' in before
    assert 'for="agent-max-tokens"' in before


def test_agent_config_max_tokens_in_agent_section():
    """The max_tokens field is in the agent configuration section."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    section_start = html.index('AGENTE IA')
    section_end = html.index('</section>', section_start)
    section = html[section_start:section_end]
    assert 'id="agent-max-tokens"' in section


def test_backend_schema_has_max_tokens():
    """CompanyAgentConfig schema has max_tokens field."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig(max_tokens=256)
    assert config.max_tokens == 256


def test_backend_schema_max_tokens_optional():
    """max_tokens is optional in CompanyAgentConfig."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig()
    assert config.max_tokens is None


def test_backend_companies_router_has_max_tokens():
    """The companies router stores max_tokens in agent config."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert 'CompanyAgentConfig' in code


def test_backend_conversations_router_passes_max_tokens():
    """The conversations router passes max_tokens to agent service."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert 'max_tokens' in code
    assert 'effective_max_tokens' in code


def test_backend_agent_service_accepts_max_tokens():
    """The agent service accepts max_tokens parameter."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert 'max_tokens' in code
    assert 'num_predict' in code


def test_full_stack_max_tokens_flow():
    """End-to-end: schema validates, router stores, agent uses max_tokens."""
    from app.schemas import CompanyAgentConfig, AgentRequest
    
    # Schema accepts valid max_tokens
    config = CompanyAgentConfig(max_tokens=512)
    assert config.max_tokens == 512
    
    # Schema rejects invalid max_tokens
    from pydantic import ValidationError
    try:
        CompanyAgentConfig(max_tokens=0)
        assert False
    except ValidationError:
        pass
    
    # AgentRequest also validates
    req = AgentRequest(content="test", max_tokens=128)
    assert req.max_tokens == 128


def test_max_tokens_validator_in_both_schemas():
    """Both AgentRequest and CompanyAgentConfig validate max_tokens."""
    with open("app/schemas.py") as f:
        code = f.read()
    count = code.count('def max_tokens_positive')
    assert count == 2, f"Expected 2 max_tokens_positive validators, found {count}"

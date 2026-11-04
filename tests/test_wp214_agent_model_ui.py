"""WP-214 — Model selector in agent config UI.

The agent config UI had prompt, temperature and max_tokens fields but was
missing the model selector. Added a dropdown with common Ollama models.
"""


def test_agent_config_has_model_select():
    """The agent config form has a model select field."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="agent-model"' in html


def test_agent_model_is_select_element():
    """The model field is a select element."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="agent-model"')
    tag_start = html.rindex('<', 0, start)
    tag_end = html.index('>', start)
    tag = html[tag_start:tag_end + 1]
    assert '<select' in tag


def test_agent_model_has_default_option():
    """The model select has a default 'use default' option."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="agent-model"')
    section = html[start:start + 500]
    assert 'value=""' in section
    assert 'padrão' in section.lower() or 'default' in section.lower()


def test_agent_model_has_qwen3_option():
    """The model select includes qwen3:8b."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="agent-model"')
    section = html[start:start + 500]
    assert 'qwen3:8b' in section


def test_agent_model_has_llama_option():
    """The model select includes llama3.1:8b."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="agent-model"')
    section = html[start:start + 500]
    assert 'llama3.1:8b' in section


def test_agent_model_has_mistral_option():
    """The model select includes mistral:7b."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="agent-model"')
    section = html[start:start + 500]
    assert 'mistral:7b' in section


def test_agent_model_after_max_tokens():
    """The model field appears after max_tokens in the form."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    max_tokens_pos = html.index('id="agent-max-tokens"')
    model_pos = html.index('id="agent-model"')
    assert model_pos > max_tokens_pos


def test_agent_model_before_status():
    """The model field appears before the status message."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    model_pos = html.index('id="agent-model"')
    status_pos = html.index('id="agent-config-status"')
    assert model_pos < status_pos


def test_agent_model_has_label():
    """The model field has a label."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index('id="agent-model"')
    before = html[max(0, start - 200):start]
    assert '<label' in before
    assert 'for="agent-model"' in before


def test_app_js_loads_model():
    """app.js loadAgentConfig reads model from API response."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert 'agent-model' in js
    assert 'res.model' in js


def test_app_js_saves_model():
    """app.js save handler includes model in request body."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    save_start = js.index('agent-config-save')
    save_section = js[save_start:save_start + 800]
    assert 'body.model' in save_section


def test_app_js_model_empty_check():
    """model is only saved when non-empty."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    save_start = js.index('agent-config-save')
    save_section = js[save_start:save_start + 800]
    assert 'model !== ""' in save_section


def test_agent_config_form_has_all_fields():
    """The agent config form has all four fields: prompt, temp, max_tokens, model."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    form_start = html.index('class="agent-config-form"')
    form_end = html.index('</section>', form_start)
    form = html[form_start:form_end]
    assert 'id="agent-system-prompt"' in form
    assert 'id="agent-temperature"' in form
    assert 'id="agent-max-tokens"' in form
    assert 'id="agent-model"' in form


def test_model_select_in_agent_section():
    """The model select is in the agent configuration section."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    section_start = html.index('AGENTE IA')
    section_end = html.index('</section>', section_start)
    section = html[section_start:section_end]
    assert 'id="agent-model"' in section


def test_backend_schema_model_optional():
    """CompanyAgentConfig model is optional."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig()
    assert config.model is None


def test_backend_schema_model_accepts_value():
    """CompanyAgentConfig accepts model value."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig(model="llama3.1:8b")
    assert config.model == "llama3.1:8b"


def test_full_stack_model_ui_flow():
    """End-to-end: UI has model select, JS loads/saves, backend stores it."""
    # HTML has the select
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="agent-model"' in html

    # JS loads model
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert 'res.model' in js
    assert 'body.model' in js

    # Backend schema accepts model
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig(model="qwen3:8b")
    assert config.model == "qwen3:8b"

    # Backend router stores model
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert 'data.model' in code
    assert 'config["model"]' in code

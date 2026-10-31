"""WP-205 — Agent configuration UI in operator panel.

The operator can now view and edit the agent configuration (system prompt
and temperature) for their company via the "12 / AGENTE IA" section.
"""


def test_agent_config_section_exists():
    """HTML has agent config section."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert "agent-config-title" in html
    assert "12 / AGENTE IA" in html


def test_agent_config_prompt_field():
    """HTML has system prompt textarea."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="agent-system-prompt"' in html


def test_agent_config_temperature_field():
    """HTML has temperature input."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="agent-temperature"' in html


def test_agent_config_save_button():
    """HTML has save button."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="agent-config-save"' in html


def test_agent_config_status_indicator():
    """HTML has status indicator."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert 'id="agent-config-status"' in html


def test_agent_config_js_load_function():
    """JavaScript has loadAgentConfig function."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "async function loadAgentConfig" in js


def test_agent_config_js_save_handler():
    """JavaScript has save click handler."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    assert "agent-config-save" in js
    assert "addEventListener" in js


def test_agent_config_js_uses_api():
    """JavaScript uses api() to fetch and save config."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("WP-205")
    block = js[start:start + 2000]
    assert "/agent-config" in block


def test_agent_config_js_put_method():
    """JavaScript uses PUT method to save config."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("WP-205")
    block = js[start:start + 2000]
    assert '"PUT"' in block


def test_agent_config_js_reads_prompt():
    """JavaScript reads system prompt from textarea."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("WP-205")
    block = js[start:start + 2000]
    assert "agent-system-prompt" in block


def test_agent_config_js_reads_temperature():
    """JavaScript reads temperature from input."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("WP-205")
    block = js[start:start + 2000]
    assert "agent-temperature" in block


def test_agent_config_css_exists():
    """CSS has agent config styles."""
    with open("app/operator_ui/styles.css") as f:
        css = f.read()
    assert ".agent-config-form" in css
    assert ".agent-config-field" in css


def test_agent_config_section_after_briefs():
    """Agent config section comes after briefs section."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    briefs_pos = html.index("11 / BRIEFS")
    agent_pos = html.index("12 / AGENTE IA")
    assert briefs_pos < agent_pos


def test_agent_config_temperature_has_range():
    """Temperature input has min/max attributes."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    temp_start = html.index('id="agent-temperature"')
    temp_block = html[temp_start:temp_start + 200]
    assert 'min="0"' in temp_block
    assert 'max="2"' in temp_block


def test_agent_config_prompt_has_placeholder():
    """System prompt textarea has placeholder text."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    prompt_start = html.index('id="agent-system-prompt"')
    prompt_block = html[prompt_start:prompt_start + 200]
    assert "placeholder=" in prompt_block


def test_agent_config_js_success_feedback():
    """JavaScript shows success message on save."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("WP-205")
    block = js[start:start + 2000]
    assert "Salvo com sucesso" in block


def test_agent_config_js_error_feedback():
    """JavaScript shows error message on save failure."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("WP-205")
    block = js[start:start + 2000]
    assert "Erro ao salvar" in block


def test_agent_config_html_is_valid_section():
    """Agent config is a proper section element."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    assert '<section class="panel" aria-labelledby="agent-config-title">' in html


def test_agent_config_has_description():
    """Agent config section has description text."""
    with open("app/operator_ui/index.html") as f:
        html = f.read()
    start = html.index("agent-config-title")
    block = html[start:start + 500]
    assert "Configure" in block or "configure" in block


def test_agent_config_uses_company_id():
    """JavaScript uses company ID in API path."""
    with open("app/operator_ui/app.js") as f:
        js = f.read()
    start = js.index("WP-205")
    block = js[start:start + 2000]
    assert "company" in block
    assert "/companies/" in block


"""WP-202 — Custom system prompt for agent replies.

The agent service now accepts an optional system_prompt parameter,
allowing callers to override the default prompt. This prepares for
per-company configuration without requiring database migrations.
"""


def test_agent_request_has_system_prompt():
    """AgentRequest schema has optional system_prompt field."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test")
    assert req.system_prompt is None
    req2 = AgentRequest(content="test", system_prompt="custom prompt")
    assert req2.system_prompt == "custom prompt"


def test_default_system_prompt_constant():
    """Agent service has _DEFAULT_SYSTEM_PROMPT constant."""
    from app.services.agent import _DEFAULT_SYSTEM_PROMPT
    assert isinstance(_DEFAULT_SYSTEM_PROMPT, str)
    assert len(_DEFAULT_SYSTEM_PROMPT) > 0
    assert "agente" in _DEFAULT_SYSTEM_PROMPT.lower()


def test_generate_agent_reply_accepts_system_prompt():
    """generate_agent_reply accepts system_prompt parameter."""
    import inspect
    from app.services.agent import generate_agent_reply
    sig = inspect.signature(generate_agent_reply)
    params = list(sig.parameters.keys())
    assert "system_prompt" in params


def test_generate_agent_reply_system_prompt_optional():
    """system_prompt parameter is optional with None default."""
    import inspect
    from app.services.agent import generate_agent_reply
    sig = inspect.signature(generate_agent_reply)
    param = sig.parameters["system_prompt"]
    assert param.default is None


def test_conversations_router_passes_system_prompt():
    """The agent-reply endpoint passes system_prompt to generate_agent_reply."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert "system_prompt=data.system_prompt" in code


def test_agent_service_uses_custom_prompt():
    """Agent service uses custom prompt when provided."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert "system_prompt if system_prompt else" in code
    assert "_DEFAULT_SYSTEM_PROMPT" in code


def test_agent_service_prompt_fallback():
    """Agent service falls back to default when no custom prompt."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert "_DEFAULT_SYSTEM_PROMPT" in code
    # The fallback pattern
    assert "prompt = system_prompt if system_prompt else _DEFAULT_SYSTEM_PROMPT" in code


def test_agent_request_system_prompt_is_optional():
    """system_prompt defaults to None in AgentRequest."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="hello")
    assert req.system_prompt is None


def test_agent_request_system_prompt_max_length():
    """system_prompt accepts reasonable length prompts."""
    from app.schemas import AgentRequest
    long_prompt = "A " * 1000  # ~3000 chars
    req = AgentRequest(content="test", system_prompt=long_prompt)
    assert req.system_prompt == long_prompt


def test_default_prompt_content():
    """Default prompt contains expected commercial agent instructions."""
    from app.services.agent import _DEFAULT_SYSTEM_PROMPT
    assert "português" in _DEFAULT_SYSTEM_PROMPT.lower() or "objetiva" in _DEFAULT_SYSTEM_PROMPT.lower()
    assert "preços" in _DEFAULT_SYSTEM_PROMPT.lower() or "invent" in _DEFAULT_SYSTEM_PROMPT.lower()

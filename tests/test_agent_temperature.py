"""WP-203 — Configurable temperature for agent replies.

The agent service now accepts an optional temperature parameter (0.0-2.0),
allowing callers to control the creativity of the model's responses.
This complements the system_prompt parameter (WP-202) and prepares for
per-company configuration (F3) without database migrations.
"""


def test_agent_request_has_temperature():
    """AgentRequest schema has optional temperature field."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test")
    assert req.temperature is None
    req2 = AgentRequest(content="test", temperature=0.5)
    assert req2.temperature == 0.5


def test_agent_request_temperature_is_optional():
    """temperature defaults to None in AgentRequest."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="hello")
    assert req.temperature is None


def test_generate_agent_reply_accepts_temperature():
    """generate_agent_reply accepts temperature parameter."""
    import inspect
    from app.services.agent import generate_agent_reply
    sig = inspect.signature(generate_agent_reply)
    params = list(sig.parameters.keys())
    assert "temperature" in params


def test_generate_agent_reply_temperature_optional():
    """temperature parameter is optional with None default."""
    import inspect
    from app.services.agent import generate_agent_reply
    sig = inspect.signature(generate_agent_reply)
    param = sig.parameters["temperature"]
    assert param.default is None


def test_conversations_router_passes_temperature():
    """The agent-reply endpoint passes temperature to generate_agent_reply."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    # WP-204 changed to use effective_temp with company config fallback
    assert "temperature=effective_temp" in code or "temperature=data.temperature" in code


def test_agent_service_uses_temperature():
    """Agent service includes temperature in options when provided."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert '"options"' in code
    assert '"temperature"' in code
    assert "if temperature is not None" in code


def test_agent_service_temperature_in_options():
    """Temperature is passed inside the options dict."""
    with open("app/services/agent.py") as f:
        code = f.read()
    # WP-208 changed to use options dict pattern
    assert 'options["temperature"] = temperature' in code or 'body["options"] = {"temperature": temperature}' in code


def test_agent_service_no_temperature_by_default():
    """Agent service does not add options when temperature is None."""
    with open("app/services/agent.py") as f:
        code = f.read()
    # The options are only added conditionally
    assert "if temperature is not None" in code


def test_temperature_accepts_float():
    """temperature field accepts float values."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", temperature=0.7)
    assert req.temperature == 0.7


def test_temperature_accepts_zero():
    """temperature field accepts 0.0 (most deterministic)."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", temperature=0.0)
    assert req.temperature == 0.0


def test_temperature_accepts_high_value():
    """temperature field accepts values up to 2.0."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", temperature=1.5)
    assert req.temperature == 1.5


def test_agent_request_has_both_prompt_and_temperature():
    """AgentRequest has both system_prompt and temperature."""
    from app.schemas import AgentRequest
    req = AgentRequest(
        content="test",
        system_prompt="custom prompt",
        temperature=0.3,
    )
    assert req.system_prompt == "custom prompt"
    assert req.temperature == 0.3


def test_agent_request_defaults():
    """AgentRequest defaults: both optional fields are None."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test")
    assert req.system_prompt is None
    assert req.temperature is None


def test_generate_agent_reply_signature():
    """generate_agent_reply has message, history, system_prompt, temperature."""
    import inspect
    from app.services.agent import generate_agent_reply
    sig = inspect.signature(generate_agent_reply)
    params = list(sig.parameters.keys())
    assert "message" in params
    assert "history" in params
    assert "system_prompt" in params
    assert "temperature" in params


def test_temperature_is_float_type():
    """temperature parameter is typed as float | None."""
    import inspect
    from app.services.agent import generate_agent_reply
    sig = inspect.signature(generate_agent_reply)
    param = sig.parameters["temperature"]
    annotation = str(param.annotation)
    assert "float" in annotation


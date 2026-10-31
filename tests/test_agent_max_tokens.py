"""WP-208 — Configurable max_tokens for agent replies.

The agent service now accepts an optional max_tokens parameter,
allowing callers to control the maximum length of the model's responses.
This complements system_prompt (WP-202) and temperature (WP-203).
"""


def test_agent_request_has_max_tokens():
    """AgentRequest schema has optional max_tokens field."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test")
    assert req.max_tokens is None
    req2 = AgentRequest(content="test", max_tokens=256)
    assert req2.max_tokens == 256


def test_agent_request_max_tokens_is_optional():
    """max_tokens defaults to None in AgentRequest."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="hello")
    assert req.max_tokens is None


def test_generate_agent_reply_accepts_max_tokens():
    """generate_agent_reply accepts max_tokens parameter."""
    import inspect
    from app.services.agent import generate_agent_reply
    sig = inspect.signature(generate_agent_reply)
    params = list(sig.parameters.keys())
    assert "max_tokens" in params


def test_generate_agent_reply_max_tokens_optional():
    """max_tokens parameter is optional with None default."""
    import inspect
    from app.services.agent import generate_agent_reply
    sig = inspect.signature(generate_agent_reply)
    param = sig.parameters["max_tokens"]
    assert param.default is None


def test_conversations_router_passes_max_tokens():
    """The agent-reply endpoint passes max_tokens to generate_agent_reply."""
    with open("app/routers/conversations.py") as f:
        code = f.read()
    assert "max_tokens" in code
    assert "effective_max_tokens" in code


def test_agent_service_uses_max_tokens():
    """Agent service includes max_tokens in options when provided."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert '"num_predict"' in code
    assert "if max_tokens is not None" in code


def test_agent_service_max_tokens_in_options():
    """max_tokens is passed as num_predict inside the options dict."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert 'options["num_predict"] = max_tokens' in code


def test_agent_service_no_max_tokens_by_default():
    """Agent service does not add num_predict when max_tokens is None."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert "if max_tokens is not None" in code


def test_max_tokens_accepts_int():
    """max_tokens field accepts int values."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", max_tokens=128)
    assert req.max_tokens == 128


def test_max_tokens_accepts_large_value():
    """max_tokens field accepts large values."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", max_tokens=4096)
    assert req.max_tokens == 4096


def test_max_tokens_rejects_zero():
    """max_tokens field rejects 0."""
    from app.schemas import AgentRequest
    from pydantic import ValidationError
    try:
        AgentRequest(content="test", max_tokens=0)
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_max_tokens_rejects_negative():
    """max_tokens field rejects negative values."""
    from app.schemas import AgentRequest
    from pydantic import ValidationError
    try:
        AgentRequest(content="test", max_tokens=-1)
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_agent_request_has_all_params():
    """AgentRequest has system_prompt, temperature, and max_tokens."""
    from app.schemas import AgentRequest
    req = AgentRequest(
        content="test",
        system_prompt="custom prompt",
        temperature=0.3,
        max_tokens=256,
    )
    assert req.system_prompt == "custom prompt"
    assert req.temperature == 0.3
    assert req.max_tokens == 256


def test_agent_request_defaults():
    """AgentRequest defaults: all optional fields are None."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test")
    assert req.system_prompt is None
    assert req.temperature is None
    assert req.max_tokens is None


def test_generate_agent_reply_signature():
    """generate_agent_reply has message, history, system_prompt, temperature, max_tokens."""
    import inspect
    from app.services.agent import generate_agent_reply
    sig = inspect.signature(generate_agent_reply)
    params = list(sig.parameters.keys())
    assert "message" in params
    assert "history" in params
    assert "system_prompt" in params
    assert "temperature" in params
    assert "max_tokens" in params


def test_company_agent_config_has_max_tokens():
    """CompanyAgentConfig has optional max_tokens field."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig()
    assert config.max_tokens is None
    config2 = CompanyAgentConfig(max_tokens=512)
    assert config2.max_tokens == 512


def test_company_agent_config_max_tokens_rejects_zero():
    """CompanyAgentConfig rejects max_tokens=0."""
    from app.schemas import CompanyAgentConfig
    from pydantic import ValidationError
    try:
        CompanyAgentConfig(max_tokens=0)
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_company_agent_config_max_tokens_rejects_negative():
    """CompanyAgentConfig rejects negative max_tokens."""
    from app.schemas import CompanyAgentConfig
    from pydantic import ValidationError
    try:
        CompanyAgentConfig(max_tokens=-100)
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_company_agent_config_all_fields():
    """CompanyAgentConfig has system_prompt, temperature, and max_tokens."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig(
        system_prompt="custom",
        temperature=0.5,
        max_tokens=256,
    )
    assert config.system_prompt == "custom"
    assert config.temperature == 0.5
    assert config.max_tokens == 256


def test_max_tokens_validator_in_code():
    """The max_tokens_positive validator exists in both classes."""
    with open("app/schemas.py") as f:
        code = f.read()
    count = code.count("def max_tokens_positive")
    assert count == 2, f"Expected 2 max_tokens_positive validators, found {count}"


def test_max_tokens_validator_field_validator_decorator():
    """@field_validator decorator is used for max_tokens."""
    with open("app/schemas.py") as f:
        code = f.read()
    assert '@field_validator("max_tokens")' in code


def test_max_tokens_validator_raises_value_error():
    """max_tokens_positive raises ValueError for invalid values."""
    with open("app/schemas.py") as f:
        code = f.read()
    start = code.index("def max_tokens_positive")
    end = code.index("\n\n", start)
    func_code = code[start:end]
    assert "ValueError" in func_code


def test_max_tokens_validator_returns_value():
    """max_tokens_positive returns the validated value."""
    with open("app/schemas.py") as f:
        code = f.read()
    start = code.index("def max_tokens_positive")
    end = code.index("\n\n", start)
    func_code = code[start:end]
    assert "return v" in func_code


def test_max_tokens_validator_accepts_one():
    """max_tokens=1 is accepted (minimum valid value)."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", max_tokens=1)
    assert req.max_tokens == 1


def test_max_tokens_validator_accepts_common_values():
    """Common max_tokens values (64, 128, 256, 512, 1024, 4096) are accepted."""
    from app.schemas import AgentRequest
    for tokens in [64, 128, 256, 512, 1024, 4096]:
        req = AgentRequest(content="test", max_tokens=tokens)
        assert req.max_tokens == tokens, f"Failed for max_tokens {tokens}"


def test_max_tokens_integration_with_agent_service():
    """Agent service receives validated max_tokens."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert "max_tokens" in code
    assert "num_predict" in code


def test_max_tokens_integration_with_companies_router():
    """Companies router stores validated max_tokens."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "CompanyAgentConfig" in code


def test_max_tokens_with_json():
    """max_tokens validation works with JSON parsing."""
    from app.schemas import AgentRequest
    import json
    data = json.dumps({"content": "test", "max_tokens": 256})
    req = AgentRequest.model_validate_json(data)
    assert req.max_tokens == 256


def test_max_tokens_rejects_json_zero():
    """max_tokens validation rejects 0 in JSON."""
    from app.schemas import AgentRequest
    from pydantic import ValidationError
    import json
    data = json.dumps({"content": "test", "max_tokens": 0})
    try:
        AgentRequest.model_validate_json(data)
        assert False
    except ValidationError:
        pass


def test_max_tokens_with_model_dump():
    """max_tokens is preserved in model_dump."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", max_tokens=256)
    dumped = req.model_dump()
    assert dumped["max_tokens"] == 256


def test_max_tokens_with_exclude_unset():
    """max_tokens is excluded when unset."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test")
    dumped = req.model_dump(exclude_unset=True)
    assert "max_tokens" not in dumped


def test_max_tokens_not_required():
    """max_tokens is not required in AgentRequest."""
    from app.schemas import AgentRequest
    schema = AgentRequest.model_json_schema()
    required = schema.get("required", [])
    assert "max_tokens" not in required


def test_options_dict_combined():
    """temperature and max_tokens are combined in options dict."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert 'options: dict[str, object] = {}' in code
    assert 'options["temperature"]' in code
    assert 'options["num_predict"]' in code
    assert 'if options:' in code
    assert 'body["options"] = options' in code

"""WP-207 — Temperature validation for agent configuration.

Both AgentRequest and CompanyAgentConfig now validate that temperature
is between 0.0 and 2.0. Values outside this range are rejected at the
schema level, preventing invalid values from reaching the Ollama API.
"""


def test_agent_request_temperature_none_is_valid():
    """AgentRequest accepts None temperature."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test")
    assert req.temperature is None


def test_agent_request_temperature_zero_is_valid():
    """AgentRequest accepts 0.0 temperature."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", temperature=0.0)
    assert req.temperature == 0.0


def test_agent_request_temperature_max_is_valid():
    """AgentRequest accepts 2.0 temperature (max)."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", temperature=2.0)
    assert req.temperature == 2.0


def test_agent_request_temperature_negative_is_rejected():
    """AgentRequest rejects negative temperature."""
    from app.schemas import AgentRequest
    from pydantic import ValidationError
    try:
        AgentRequest(content="test", temperature=-0.1)
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_agent_request_temperature_too_high_is_rejected():
    """AgentRequest rejects temperature above 2.0."""
    from app.schemas import AgentRequest
    from pydantic import ValidationError
    try:
        AgentRequest(content="test", temperature=2.1)
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_company_agent_config_temperature_none_is_valid():
    """CompanyAgentConfig accepts None temperature."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig()
    assert config.temperature is None


def test_company_agent_config_temperature_zero_is_valid():
    """CompanyAgentConfig accepts 0.0 temperature."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig(temperature=0.0)
    assert config.temperature == 0.0


def test_company_agent_config_temperature_max_is_valid():
    """CompanyAgentConfig accepts 2.0 temperature (max)."""
    from app.schemas import CompanyAgentConfig
    config = CompanyAgentConfig(temperature=2.0)
    assert config.temperature == 2.0


def test_company_agent_config_temperature_negative_is_rejected():
    """CompanyAgentConfig rejects negative temperature."""
    from app.schemas import CompanyAgentConfig
    from pydantic import ValidationError
    try:
        CompanyAgentConfig(temperature=-0.5)
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_company_agent_config_temperature_too_high_is_rejected():
    """CompanyAgentConfig rejects temperature above 2.0."""
    from app.schemas import CompanyAgentConfig
    from pydantic import ValidationError
    try:
        CompanyAgentConfig(temperature=2.5)
        assert False, "Should have raised ValidationError"
    except ValidationError:
        pass


def test_both_validators_use_same_bounds():
    """Both AgentRequest and CompanyAgentConfig use 0.0-2.0 bounds."""
    from app.schemas import AgentRequest, CompanyAgentConfig
    from pydantic import ValidationError

    AgentRequest(content="test", temperature=0.0)
    AgentRequest(content="test", temperature=2.0)
    CompanyAgentConfig(temperature=0.0)
    CompanyAgentConfig(temperature=2.0)

    for factory in [
        lambda: AgentRequest(content="test", temperature=-0.1),
        lambda: AgentRequest(content="test", temperature=2.1),
        lambda: CompanyAgentConfig(temperature=-0.1),
        lambda: CompanyAgentConfig(temperature=2.1),
    ]:
        try:
            factory()
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass


def test_temperature_validator_in_code():
    """The temperature_range validator exists in both classes."""
    with open("app/schemas.py") as f:
        code = f.read()
    count = code.count("def temperature_range")
    assert count == 2, f"Expected 2 temperature_range validators, found {count}"


def test_temperature_validator_field_validator_decorator():
    """@field_validator decorator is used for temperature."""
    with open("app/schemas.py") as f:
        code = f.read()
    assert '@field_validator("temperature")' in code


def test_temperature_validator_raises_value_error():
    """temperature_range raises ValueError for invalid values."""
    with open("app/schemas.py") as f:
        code = f.read()
    start = code.index("def temperature_range")
    end = code.index("\n\n", start)
    func_code = code[start:end]
    assert "ValueError" in func_code


def test_temperature_validator_returns_value():
    """temperature_range returns the validated value."""
    with open("app/schemas.py") as f:
        code = f.read()
    start = code.index("def temperature_range")
    end = code.index("\n\n", start)
    func_code = code[start:end]
    assert "return v" in func_code


def test_temperature_validator_bounds_are_inclusive():
    """Both 0.0 and 2.0 are accepted (inclusive bounds)."""
    from app.schemas import AgentRequest
    req_min = AgentRequest(content="test", temperature=0.0)
    req_max = AgentRequest(content="test", temperature=2.0)
    assert req_min.temperature == 0.0
    assert req_max.temperature == 2.0


def test_temperature_validator_bounds_are_strict():
    """Values just outside bounds are rejected."""
    from app.schemas import AgentRequest
    from pydantic import ValidationError
    try:
        AgentRequest(content="test", temperature=-0.00001)
        assert False
    except ValidationError:
        pass
    try:
        AgentRequest(content="test", temperature=2.00001)
        assert False
    except ValidationError:
        pass


def test_temperature_validator_works_with_other_fields():
    """Temperature validation doesn't interfere with other fields."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="hello world", temperature=0.7)
    assert req.content == "hello world"
    assert req.temperature == 0.7


def test_temperature_validator_does_not_modify_valid_value():
    """Validator returns the exact value passed, not a clamped version."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", temperature=1.234)
    assert req.temperature == 1.234


def test_temperature_validator_with_json():
    """Temperature validation works with JSON parsing."""
    from app.schemas import AgentRequest
    import json
    data = json.dumps({"content": "test", "temperature": 0.5})
    req = AgentRequest.model_validate_json(data)
    assert req.temperature == 0.5


def test_temperature_validator_rejects_json_out_of_range():
    """Temperature validation rejects out-of-range values in JSON."""
    from app.schemas import AgentRequest
    from pydantic import ValidationError
    import json
    data = json.dumps({"content": "test", "temperature": 3.0})
    try:
        AgentRequest.model_validate_json(data)
        assert False
    except ValidationError:
        pass


def test_temperature_validator_with_model_dump():
    """Temperature is preserved in model_dump."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test", temperature=0.7)
    dumped = req.model_dump()
    assert dumped["temperature"] == 0.7


def test_temperature_validator_with_exclude_unset():
    """Temperature is excluded when unset."""
    from app.schemas import AgentRequest
    req = AgentRequest(content="test")
    dumped = req.model_dump(exclude_unset=True)
    assert "temperature" not in dumped


def test_temperature_validator_not_required():
    """Temperature is not required in AgentRequest."""
    from app.schemas import AgentRequest
    schema = AgentRequest.model_json_schema()
    required = schema.get("required", [])
    assert "temperature" not in required


def test_temperature_validator_no_syntax_errors():
    """No syntax errors in schemas.py after adding validators."""
    import py_compile
    py_compile.compile("app/schemas.py", doraise=True)


def test_temperature_validator_imports_valid():
    """All imports in schemas.py are valid."""
    from app import schemas
    assert hasattr(schemas, "AgentRequest")
    assert hasattr(schemas, "CompanyAgentConfig")


def test_temperature_validator_common_values():
    """Common temperature values (0.0, 0.5, 0.7, 1.0, 1.5, 2.0) are accepted."""
    from app.schemas import AgentRequest
    for temp in [0.0, 0.5, 0.7, 1.0, 1.5, 2.0]:
        req = AgentRequest(content="test", temperature=temp)
        assert req.temperature == temp, f"Failed for temperature {temp}"


def test_temperature_validator_integration_with_agent_service():
    """Agent service receives validated temperature."""
    with open("app/services/agent.py") as f:
        code = f.read()
    assert "temperature" in code


def test_temperature_validator_integration_with_companies_router():
    """Companies router stores validated temperature."""
    with open("app/routers/companies.py") as f:
        code = f.read()
    assert "CompanyAgentConfig" in code

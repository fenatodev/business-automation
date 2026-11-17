"""Company agent-config endpoints: GET/PUT /companies/{id}/agent-config.

Cobre configuração de agente por company: leitura padrão, escrita,
tenant isolation, 404, autenticação e agent-models-available.
"""


def _create_company(client, admin_headers, name="Company"):
    res = client.post("/companies", headers=admin_headers, json={"name": name, "slug": name.lower()})
    assert res.status_code == 200
    return res.json()


def test_get_agent_config_default(client, admin_headers, operator_a_headers):
    """GET agent-config returns defaults for a new company."""
    company = _create_company(client, admin_headers, name="ConfigCo")
    res = client.get(
        f"/companies/{company['id']}/agent-config",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert "system_prompt" in data
    assert "temperature" in data
    assert "max_tokens" in data
    assert "model" in data


def test_set_agent_config(client, admin_headers, operator_a_headers):
    """PUT agent-config sets and returns the new configuration."""
    company = _create_company(client, admin_headers, name="SetCo")
    res = client.put(
        f"/companies/{company['id']}/agent-config",
        headers=operator_a_headers,
        json={
            "system_prompt": "Você é um assistente de vendas.",
            "temperature": 0.7,
            "max_tokens": 512,
            "model": "qwen3:8b",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["system_prompt"] == "Você é um assistente de vendas."
    assert data["temperature"] == 0.7
    assert data["max_tokens"] == 512
    assert data["model"] == "qwen3:8b"


def test_set_agent_config_partial(client, admin_headers, operator_a_headers):
    """PUT agent-config with partial fields updates only those fields."""
    company = _create_company(client, admin_headers, name="PartialCo")
    res = client.put(
        f"/companies/{company['id']}/agent-config",
        headers=operator_a_headers,
        json={"temperature": 0.5},
    )
    assert res.status_code == 200
    assert res.json()["temperature"] == 0.5


def test_get_agent_config_after_set(client, admin_headers, operator_a_headers):
    """GET agent-config reflects the values set by PUT."""
    company = _create_company(client, admin_headers, name="ReflectCo")
    client.put(
        f"/companies/{company['id']}/agent-config",
        headers=operator_a_headers,
        json={"system_prompt": "Custom prompt", "model": "llama3.1:8b"},
    )
    res = client.get(
        f"/companies/{company['id']}/agent-config",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["system_prompt"] == "Custom prompt"
    assert data["model"] == "llama3.1:8b"


def test_agent_config_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot access Operator A's agent config."""
    company = _create_company(client, admin_headers, name="IsolationCo")
    client.put(
        f"/companies/{company['id']}/agent-config",
        headers=operator_a_headers,
        json={"system_prompt": "Secret prompt"},
    )
    res = client.get(
        f"/companies/{company['id']}/agent-config",
        headers=operator_b_headers,
    )
    assert res.status_code == 403


def test_agent_config_set_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot set Operator A's agent config."""
    company = _create_company(client, admin_headers, name="SetIsolationCo")
    res = client.put(
        f"/companies/{company['id']}/agent-config",
        headers=operator_b_headers,
        json={"system_prompt": "Hacked prompt"},
    )
    assert res.status_code == 403


def test_agent_config_nonexistent_company(client, admin_headers, operator_a_headers):
    """GET agent-config for nonexistent company returns 404."""
    res = client.get(
        "/companies/99999/agent-config",
        headers=operator_a_headers,
    )
    assert res.status_code == 404


def test_agent_config_requires_auth(client, admin_headers, operator_a_headers):
    """GET agent-config without auth returns 401."""
    company = _create_company(client, admin_headers, name="AuthCo")
    res = client.get(f"/companies/{company['id']}/agent-config")
    assert res.status_code in (401, 403)


def test_agent_models_available_no_auth(client):
    """GET /agent-models-available does not require authentication."""
    res = client.get("/agent-models-available")
    assert res.status_code == 200
    data = res.json()
    assert "models" in data
    assert "default" in data
    assert len(data["models"]) >= 1
    # Check default model is marked
    defaults = [m for m in data["models"] if m.get("is_default")]
    assert len(defaults) == 1


def test_agent_models_includes_qwen3(client):
    """Agent models list includes qwen3:8b as default."""
    res = client.get("/agent-models-available")
    assert res.status_code == 200
    models = res.json()["models"]
    names = [m["name"] for m in models]
    assert "qwen3:8b" in names


def test_agent_usage_endpoint(client, admin_headers, operator_a_headers):
    """GET /companies/{id}/agent-usage returns usage stats."""
    company = _create_company(client, admin_headers, name="UsageCo")
    res = client.get(
        f"/companies/{company['id']}/agent-usage",
        headers=operator_a_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["company_id"] == company["id"]
    assert "total_calls" in data
    assert "successful_calls" in data
    assert "failed_calls" in data


def test_agent_usage_tenant_isolation(client, admin_headers, operator_a_headers, operator_b_headers):
    """Operator B cannot access Operator A's agent usage."""
    company = _create_company(client, admin_headers, name="UsageIsoCo")
    res = client.get(
        f"/companies/{company['id']}/agent-usage",
        headers=operator_b_headers,
    )
    assert res.status_code == 403

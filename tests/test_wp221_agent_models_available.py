"""WP-221 — GET /agent-models-available endpoint.

Lists available Ollama models for configuration, useful for the UI dropdown.
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_agent_models_available_returns_list():
    """GET /agent-models-available returns a list of models."""
    response = client.get("/agent-models-available")
    assert response.status_code == 200
    data = response.json()
    assert "models" in data
    assert "default" in data
    assert isinstance(data["models"], list)
    assert len(data["models"]) >= 5


def test_agent_models_available_includes_qwen3():
    """The model list includes qwen3:8b."""
    response = client.get("/agent-models-available")
    data = response.json()
    names = [m["name"] for m in data["models"]]
    assert "qwen3:8b" in names


def test_agent_models_available_includes_llama():
    """The model list includes llama3.1:8b."""
    response = client.get("/agent-models-available")
    data = response.json()
    names = [m["name"] for m in data["models"]]
    assert "llama3.1:8b" in names


def test_agent_models_available_includes_mistral():
    """The model list includes mistral:7b."""
    response = client.get("/agent-models-available")
    data = response.json()
    names = [m["name"] for m in data["models"]]
    assert "mistral:7b" in names


def test_agent_models_available_has_labels():
    """Each model has a name and a label."""
    response = client.get("/agent-models-available")
    data = response.json()
    for model in data["models"]:
        assert "name" in model
        assert "label" in model
        assert "is_default" in model


def test_agent_models_available_marks_default():
    """The default model is marked as is_default=True."""
    response = client.get("/agent-models-available")
    data = response.json()
    defaults = [m for m in data["models"] if m["is_default"]]
    assert len(defaults) == 1
    assert data["default"] == defaults[0]["name"]


def test_agent_models_available_no_auth_required():
    """The endpoint does not require authentication."""
    response = client.get("/agent-models-available")
    assert response.status_code == 200


def test_agent_models_available_default_matches_setting():
    """The default model matches settings.ollama_model."""
    from app.database import settings
    response = client.get("/agent-models-available")
    data = response.json()
    assert data["default"] == settings.ollama_model


def test_agent_models_available_includes_gemma():
    """The model list includes gemma2:9b."""
    response = client.get("/agent-models-available")
    data = response.json()
    names = [m["name"] for m in data["models"]]
    assert "gemma2:9b" in names


def test_agent_models_available_includes_qwen25():
    """The model list includes qwen2.5:7b."""
    response = client.get("/agent-models-available")
    data = response.json()
    names = [m["name"] for m in data["models"]]
    assert "qwen2.5:7b" in names

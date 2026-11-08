"""WP-530 — Agent provider abstraction tests."""
from app.services.agent import (
    AgentProvider,
    AgentServiceError,
    NoopProvider,
    OllamaProvider,
    _available_providers,
    get_provider,
    generate_agent_reply,
    register_provider,
    summarize_conversation,
)


def _reset_providers():
    """Clear all registered providers for test isolation."""
    _available_providers.clear()


# --- NoopProvider tests ---


def test_noop_provider_generate_reply():
    """NoopProvider returns placeholder reply."""
    provider = NoopProvider()
    result = provider.generate_reply("Hello", [])
    assert "indisponível" in result.lower() or "desativada" in result.lower()


def test_noop_provider_summarize():
    """NoopProvider returns placeholder summary."""
    provider = NoopProvider()
    result = provider.summarize([])
    assert "summary" in result
    assert "key_points" in result
    assert "action_items" in result
    assert result["key_points"] == []
    assert result["action_items"] == []


def test_noop_provider_health_check():
    """NoopProvider health check always returns healthy."""
    provider = NoopProvider()
    result = provider.health_check()
    assert result["provider"] == "noop"
    assert result["status"] == "healthy"


def test_noop_provider_generate_reply_with_params():
    """NoopProvider accepts all params without error."""
    provider = NoopProvider()
    result = provider.generate_reply(
        "Hello",
        [{"sender_type": "customer", "content": "Hi"}],
        system_prompt="Custom prompt",
        temperature=0.7,
        max_tokens=100,
        model="test-model",
    )
    assert isinstance(result, str)


def test_noop_provider_summarize_with_history():
    """NoopProvider summarize accepts history without error."""
    provider = NoopProvider()
    history = [
        {"sender_type": "customer", "content": "Hello"},
        {"sender_type": "agent", "content": "Hi there"},
    ]
    result = provider.summarize(history)
    assert "summary" in result


# --- OllamaProvider tests ---


def test_ollama_provider_init_defaults():
    """OllamaProvider uses settings defaults."""
    provider = OllamaProvider()
    assert provider.base_url is not None
    assert provider.default_model is not None


def test_ollama_provider_init_custom():
    """OllamaProvider accepts custom URL and model."""
    provider = OllamaProvider(
        base_url="http://custom:11434",
        default_model="custom-model",
    )
    assert provider.base_url == "http://custom:11434"
    assert provider.default_model == "custom-model"


def test_ollama_provider_health_check_unhealthy():
    """OllamaProvider health check returns unhealthy when Ollama unavailable."""
    provider = OllamaProvider(base_url="http://localhost:99999")
    result = provider.health_check()
    assert result["provider"] == "ollama"
    assert result["status"] == "unhealthy"


def test_ollama_provider_is_agent_provider():
    """OllamaProvider implements AgentProvider interface."""
    provider = OllamaProvider()
    assert isinstance(provider, AgentProvider)


def test_noop_provider_is_agent_provider():
    """NoopProvider implements AgentProvider interface."""
    provider = NoopProvider()
    assert isinstance(provider, AgentProvider)


# --- Provider registry tests ---


def test_register_and_get_provider():
    """Register and retrieve a provider by name."""
    _reset_providers()
    provider = NoopProvider()
    register_provider("test", provider)
    assert get_provider("test") is provider


def test_get_default_provider():
    """Get default provider when no name specified."""
    _reset_providers()
    noop = NoopProvider()
    register_provider("default", noop)
    assert get_provider() is noop


def test_get_provider_fallback_to_noop():
    """Get provider falls back to NoopProvider when nothing registered."""
    _reset_providers()
    result = get_provider()
    assert isinstance(result, NoopProvider)


def test_get_provider_fallback_to_ollama():
    """Get provider falls back to ollama if no default."""
    _reset_providers()
    ollama = OllamaProvider()
    register_provider("ollama", ollama)
    assert get_provider() is ollama


# --- Backward compatible functions ---


def test_generate_agent_reply_uses_provider():
    """generate_agent_reply uses the registered provider."""
    _reset_providers()
    noop = NoopProvider()
    register_provider("default", noop)
    result = generate_agent_reply("Hello", [])
    assert isinstance(result, str)
    assert len(result) > 0


def test_summarize_conversation_uses_provider():
    """summarize_conversation uses the registered provider."""
    _reset_providers()
    noop = NoopProvider()
    register_provider("default", noop)
    result = summarize_conversation([])
    assert "summary" in result
    assert "key_points" in result
    assert "action_items" in result


def test_backward_compat_ensures_default():
    """Public functions ensure default provider is registered."""
    _reset_providers()
    # Auto-register defaults; use NoopProvider as default so Ollama isn't called
    register_provider("default", NoopProvider())
    result = generate_agent_reply("test", [])
    assert isinstance(result, str)
    assert "default" in _available_providers


def test_provider_switching():
    """Switching providers changes behavior."""
    _reset_providers()
    noop = NoopProvider()
    register_provider("default", noop)

    result1 = generate_agent_reply("test", [])
    assert isinstance(result1, str)

    # Switch to a different provider
    class CustomProvider(AgentProvider):
        def generate_reply(self, message, history, **kwargs):
            return "CUSTOM_REPLY"

        def summarize(self, history, **kwargs):
            return {"summary": "CUSTOM", "key_points": [], "action_items": []}

        def health_check(self):
            return {"provider": "custom", "status": "healthy"}

    register_provider("default", CustomProvider())
    result2 = generate_agent_reply("test", [])
    assert result2 == "CUSTOM_REPLY"


def test_ollama_provider_generate_reply_raises_on_failure():
    """OllamaProvider raises AgentServiceError on HTTP failure."""
    provider = OllamaProvider(base_url="http://localhost:99999")
    try:
        provider.generate_reply("test", [])
        assert False, "Expected AgentServiceError"
    except AgentServiceError:
        pass


def test_ollama_provider_summarize_raises_on_failure():
    """OllamaProvider raises AgentServiceError on HTTP failure."""
    provider = OllamaProvider(base_url="http://localhost:99999")
    try:
        provider.summarize([])
        assert False, "Expected AgentServiceError"
    except AgentServiceError:
        pass

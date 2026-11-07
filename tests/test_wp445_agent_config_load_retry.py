from pathlib import Path
import subprocess


def test_agent_config_retry_control_exists():
    html = Path("app/operator_ui/index.html").read_text()
    assert 'id="agent-config-load-retry"' in html
    assert 'id="agent-config-form"' in html
    assert 'role="status" aria-live="polite"' in html


def test_agent_config_retry_behavior():
    subprocess.run(["node", "tests/js/agent_config_load_retry.cjs"], check=True)

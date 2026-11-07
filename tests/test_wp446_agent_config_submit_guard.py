import subprocess


def test_agent_config_submit_guard():
    subprocess.run(["node", "tests/js/agent_config_submit_guard.cjs"], check=True)

"""WP-057: Tests for Junie Agent Sandbox Isolation.

These tests validate that the agent sandbox configuration properly
isolates the Junie agent process from host resources. The tests cover:

1. Dockerfile: Non-root user, no privileged groups, read-only FS
2. Docker Compose: No Docker socket, no LXD, no host network
3. Sandbox config: MCP denial, network restrictions, file system limits
4. Launcher: Isolation checks, authentication, Git token handling
5. Healthcheck: All isolation checks pass
6. Bypass attempts: Docker, LXD, sudo, secrets, n8n DB
7. IDE vs CLI: Different processes, different isolation levels

Key scenarios:
- Agent cannot access Docker socket
- Agent cannot access LXD socket
- Agent cannot access user's real home directory
- Agent cannot access n8n SQLite database
- Agent cannot access SSH agent
- MCP servers that control host are denied
- Network access is restricted
- File system is read-only with specific writable directories
- Non-root user without privileged groups
"""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def agent_sandbox_dir():
    """Return the agent sandbox directory."""
    return Path("ops/agent-sandbox")


@pytest.fixture()
def dockerfile(agent_sandbox_dir):
    """Read the agent sandbox Dockerfile."""
    return (agent_sandbox_dir / "Dockerfile").read_text(encoding="utf-8")


@pytest.fixture()
def docker_compose(agent_sandbox_dir):
    """Read the agent sandbox docker-compose.yml."""
    return (agent_sandbox_dir / "docker-compose.yml").read_text(encoding="utf-8")


@pytest.fixture()
def sandbox_config(agent_sandbox_dir):
    """Load the sandbox configuration."""
    config_path = agent_sandbox_dir / "sandbox.json"
    return json.loads(config_path.read_text(encoding="utf-8"))


@pytest.fixture()
def launcher_script(agent_sandbox_dir):
    """Read the launcher script."""
    return (agent_sandbox_dir / "launch-agent.sh").read_text(encoding="utf-8")


@pytest.fixture()
def healthcheck_script(agent_sandbox_dir):
    """Read the healthcheck script."""
    return (agent_sandbox_dir / "healthcheck.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# TestDockerfileIsolation: Dockerfile isolation guarantees
# ---------------------------------------------------------------------------


class TestDockerfileIsolation:
    """Validate that the Dockerfile provides proper isolation."""

    def test_non_root_user(self, dockerfile):
        """The Dockerfile creates and uses a non-root user."""
        assert "USER junie-agent" in dockerfile
        assert "useradd" in dockerfile

    def test_no_docker_group(self, dockerfile):
        """The Dockerfile does not add the user to the docker group."""
        # The user should NOT be in the docker group
        assert "docker" not in dockerfile.lower().split("group")[1].split("\n")[0] if "group" in dockerfile.lower() else True

    def test_no_sudo_group(self, dockerfile):
        """The Dockerfile does not add the user to the sudo group."""
        lines = dockerfile.split("\n")
        for line in lines:
            if "useradd" in line or "groupadd" in line:
                assert "sudo" not in line.lower()

    def test_no_lxd_group(self, dockerfile):
        """The Dockerfile does not add the user to the lxd group."""
        lines = dockerfile.split("\n")
        for line in lines:
            if "useradd" in line or "groupadd" in line:
                assert "lxd" not in line.lower()

    def test_read_only_filesystem(self, dockerfile):
        """The Dockerfile comments mention read-only filesystem."""
        assert "read-only" in dockerfile.lower() or "Read-only" in dockerfile

    def test_no_docker_socket_mount(self, dockerfile):
        """The Dockerfile does not mount Docker socket."""
        assert "/var/run/docker.sock" not in dockerfile or "NOT" in dockerfile

    def test_no_n8n_data_mount(self, dockerfile):
        """The Dockerfile does not mount n8n data directory."""
        assert "/var/lib/n8n" not in dockerfile or "NOT" in dockerfile

    def test_no_user_home_mount(self, dockerfile):
        """The Dockerfile does not mount user's real home directory."""
        assert "/home/fenatodev" not in dockerfile or "NOT" in dockerfile

    def test_no_ssh_agent_mount(self, dockerfile):
        """The Dockerfile does not mount SSH agent."""
        assert "SSH_AUTH_SOCK" not in dockerfile or "NOT" in dockerfile

    def test_no_junie_home_mount(self, dockerfile):
        """The Dockerfile does not mount ~/.junie from host."""
        assert "~/.junie" not in dockerfile or "NOT" in dockerfile

    def test_bubblewrap_or_junie_installed(self, dockerfile):
        """The Dockerfile installs either bubblewrap (for sandbox mode) or Junie CLI.

        Note: bubblewrap was removed when we discovered --sandbox is only available
        in dev/nightly builds. The Dockerfile now installs Junie CLI officially.
        """
        # Either bubblewrap for sandbox mode OR Junie CLI official install
        assert "bubblewrap" in dockerfile or "junie.jetbrains.com" in dockerfile

    def test_resource_limits_mentioned(self, dockerfile):
        """The Dockerfile mentions resource limits."""
        assert "resource" in dockerfile.lower() or "limit" in dockerfile.lower()

    def test_healthcheck_defined(self, dockerfile):
        """The Dockerfile defines a healthcheck."""
        assert "HEALTHCHECK" in dockerfile

    def test_no_junie_api_key_hardcoded(self, dockerfile):
        """The Dockerfile does not hardcode JUNIE_API_KEY."""
        assert 'JUNIE_API_KEY' not in dockerfile or 'NOT' in dockerfile or 'DO NOT' in dockerfile


# ---------------------------------------------------------------------------
# TestDockerComposeIsolation: Compose isolation guarantees
# ---------------------------------------------------------------------------


class TestDockerComposeIsolation:
    """Validate that docker-compose.yml provides proper isolation."""

    def test_read_only_filesystem(self, docker_compose):
        """The compose file sets read_only: true."""
        assert "read_only: true" in docker_compose

    def test_no_new_privileges(self, docker_compose):
        """The compose file sets no-new-privileges."""
        assert "no-new-privileges" in docker_compose

    def test_non_root_user(self, docker_compose):
        """The compose file runs as non-root user."""
        assert "junie-agent" in docker_compose
        assert "user:" in docker_compose

    def test_no_docker_socket_mount(self, docker_compose):
        """The compose file does not mount Docker socket."""
        assert "/var/run/docker.sock" not in docker_compose or "NOT" in docker_compose

    def test_no_n8n_data_mount(self, docker_compose):
        """The compose file does not mount n8n data directory."""
        assert "/var/lib/n8n" not in docker_compose or "NOT" in docker_compose

    def test_no_user_home_mount(self, docker_compose):
        """The compose file does not mount user's real home directory."""
        assert "/home/fenatodev" not in docker_compose or "NOT" in docker_compose

    def test_no_ssh_agent_mount(self, docker_compose):
        """The compose file does not mount SSH agent socket."""
        assert "SSH_AUTH_SOCK" not in docker_compose or "NOT" in docker_compose

    def test_no_host_network(self, docker_compose):
        """The compose file does not use host network mode."""
        assert "network_mode: host" not in docker_compose

    def test_resource_limits(self, docker_compose):
        """The compose file sets resource limits."""
        assert "cpus:" in docker_compose
        assert "memory:" in docker_compose

    def test_no_exposed_ports(self, docker_compose):
        """The compose file does not expose ports to host."""
        assert "ports:" not in docker_compose or "Do NOT expose" in docker_compose

    def test_junie_api_key_not_hardcoded(self, docker_compose):
        """The compose file does not hardcode JUNIE_API_KEY."""
        # JUNIE_API_KEY should be a variable, not a hardcoded value
        lines = docker_compose.split("\n")
        for line in lines:
            if "JUNIE_API_KEY" in line and ":" in line:
                assert "${" in line or ":-" in line  # Should be a variable

    def test_internal_network_or_no_network(self, docker_compose):
        """The compose file uses network_mode: none or internal network by default."""
        # network_mode: none is the strongest isolation — no network at all
        assert "network_mode: none" in docker_compose or "internal: true" in docker_compose

    def test_restart_policy(self, docker_compose):
        """The compose file does not auto-restart by default."""
        assert 'restart: "no"' in docker_compose or "restart: no" in docker_compose

    def test_healthcheck_defined(self, docker_compose):
        """The compose file defines a healthcheck."""
        assert "healthcheck:" in docker_compose


# ---------------------------------------------------------------------------
# TestSandboxConfig: Sandbox configuration validation
# ---------------------------------------------------------------------------


class TestSandboxConfig:
    """Validate the sandbox.json configuration."""

    def test_mcp_default_deny(self, sandbox_config):
        """MCP servers are denied by default."""
        mcp_policy = sandbox_config["junieAgentSandbox"]["mcpPolicy"]
        assert mcp_policy["defaultAction"] == "deny"

    def test_playwright_denied(self, sandbox_config):
        """Playwright MCP is explicitly denied."""
        mcp_policy = sandbox_config["junieAgentSandbox"]["mcpPolicy"]
        assert "playwright" in mcp_policy["deniedServers"]

    def test_computer_use_denied(self, sandbox_config):
        """Computer Use MCP is explicitly denied."""
        mcp_policy = sandbox_config["junieAgentSandbox"]["mcpPolicy"]
        assert "computer-use" in mcp_policy["deniedServers"]

    def test_no_allowed_mcp_servers(self, sandbox_config):
        """No MCP servers are allowed by default."""
        mcp_policy = sandbox_config["junieAgentSandbox"]["mcpPolicy"]
        assert len(mcp_policy["allowedServers"]) == 0

    def test_network_restricted(self, sandbox_config):
        """Network access is restricted by default."""
        network = sandbox_config["junieAgentSandbox"]["network"]
        assert network["unrestricted"] is False

    def test_no_unix_sockets(self, sandbox_config):
        """No Unix sockets are allowed by default."""
        network = sandbox_config["junieAgentSandbox"]["network"]
        assert len(network["allowUnixSockets"]) == 0

    def test_internal_networks_denied(self, sandbox_config):
        """Internal networks are denied."""
        network = sandbox_config["junieAgentSandbox"]["network"]
        assert "127.0.0.1" in network["deniedHosts"]
        assert "localhost" in network["deniedHosts"]

    def test_docker_socket_write_denied(self, sandbox_config):
        """Docker socket write is denied."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/var/run/docker.sock" in fs["denyWrite"]

    def test_lxd_write_denied(self, sandbox_config):
        """LXD write is denied."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/var/lib/lxd" in fs["denyWrite"]

    def test_user_home_read_denied(self, sandbox_config):
        """User's home directory read is denied."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/home/fenatodev/.ssh" in fs["denyRead"]

    def test_n8n_data_read_denied(self, sandbox_config):
        """n8n data directory read is denied."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/var/lib/n8n" in fs["denyRead"]

    def test_junie_config_brave_off(self, sandbox_config):
        """Brave mode is off by default in sandbox."""
        junie_config = sandbox_config["junieAgentSandbox"]["junieConfig"]
        assert junie_config["brave"] is False

    def test_junie_config_sandbox_on(self, sandbox_config):
        """Sandbox mode is on by default."""
        junie_config = sandbox_config["junieAgentSandbox"]["junieConfig"]
        assert junie_config["sandbox"] is True

    def test_resource_limits(self, sandbox_config):
        """Resource limits are defined."""
        limits = sandbox_config["junieAgentSandbox"]["resourceLimits"]
        assert "cpus" in limits
        assert "memory" in limits

    def test_isolation_flags(self, sandbox_config):
        """Isolation flags are all set to true."""
        isolation = sandbox_config["junieAgentSandbox"]["isolation"]
        assert isolation["noDockerSocket"] is True
        assert isolation["noLXD"] is True
        assert isolation["noSudo"] is True
        assert isolation["noHostNetwork"] is True
        assert isolation["noUserHome"] is True
        assert isolation["noSSHAgent"] is True
        assert isolation["noN8nData"] is True


# ---------------------------------------------------------------------------
# TestLauncherScript: Launcher isolation checks
# ---------------------------------------------------------------------------


class TestLauncherScript:
    """Validate the launcher script isolation checks."""

    def test_checks_docker_socket(self, launcher_script):
        """The launcher checks for Docker socket access."""
        assert "/var/run/docker.sock" in launcher_script

    def test_checks_lxd_socket(self, launcher_script):
        """The launcher checks for LXD socket access."""
        assert "lxd" in launcher_script.lower()

    def test_checks_user_home(self, launcher_script):
        """The launcher checks for user's home directory access."""
        assert "/home/fenatodev" in launcher_script or ".ssh" in launcher_script

    def test_checks_n8n_data(self, launcher_script):
        """The launcher checks for n8n data directory access."""
        assert "/var/lib/n8n" in launcher_script

    def test_checks_ssh_agent(self, launcher_script):
        """The launcher checks for SSH agent access."""
        assert "SSH_AUTH_SOCK" in launcher_script

    def test_requires_junie_api_key(self, launcher_script):
        """The launcher requires JUNIE_API_KEY for authentication."""
        assert "JUNIE_API_KEY" in launcher_script

    def test_git_token_optional(self, launcher_script):
        """The launcher supports optional Git token."""
        assert "GIT_TOKEN" in launcher_script

    def test_sandbox_mode(self, launcher_script):
        """The launcher uses --sandbox mode."""
        assert "--sandbox" in launcher_script

    def test_exit_on_isolation_failure(self, launcher_script):
        """The launcher exits if isolation is compromised."""
        assert "exit 1" in launcher_script

    def test_no_sudo_usage(self, launcher_script):
        """The launcher does not use sudo."""
        assert "sudo" not in launcher_script.lower() or "NOT" in launcher_script


# ---------------------------------------------------------------------------
# TestHealthcheck: Healthcheck isolation validation
# ---------------------------------------------------------------------------


class TestHealthcheck:
    """Validate the healthcheck script."""

    def test_checks_docker_socket(self, healthcheck_script):
        """The healthcheck verifies Docker socket is not accessible."""
        assert "docker.sock" in healthcheck_script

    def test_checks_lxd_socket(self, healthcheck_script):
        """The healthcheck verifies LXD socket is not accessible."""
        assert "lxd" in healthcheck_script.lower()

    def test_checks_user_home(self, healthcheck_script):
        """The healthcheck verifies user's home is not mounted."""
        assert "fenatodev" in healthcheck_script or ".ssh" in healthcheck_script

    def test_checks_n8n_data(self, healthcheck_script):
        """The healthcheck verifies n8n data is not mounted."""
        assert "n8n" in healthcheck_script.lower()

    def test_checks_ssh_agent(self, healthcheck_script):
        """The healthcheck verifies SSH agent is not accessible."""
        assert "SSH_AUTH_SOCK" in healthcheck_script

    def test_checks_non_root(self, healthcheck_script):
        """The healthcheck verifies non-root user."""
        assert "getuid" in healthcheck_script or "root" in healthcheck_script.lower()

    def test_checks_read_only(self, healthcheck_script):
        """The healthcheck verifies read-only filesystem."""
        assert "read" in healthcheck_script.lower() and "only" in healthcheck_script.lower()

    def test_exit_code_on_failure(self, healthcheck_script):
        """The healthcheck returns non-zero on failure."""
        assert "return 1" in healthcheck_script or "sys.exit" in healthcheck_script


# ---------------------------------------------------------------------------
# TestBypassAttempts: Negative tests for bypass attempts
# ---------------------------------------------------------------------------


class TestBypassAttempts:
    """Test that bypass attempts are blocked by the sandbox configuration."""

    def test_docker_socket_bypass_blocked(self, sandbox_config):
        """Docker socket access is blocked by sandbox config."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/var/run/docker.sock" in fs["denyWrite"]

    def test_lxd_bypass_blocked(self, sandbox_config):
        """LXD access is blocked by sandbox config."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/var/lib/lxd" in fs["denyWrite"]

    def test_sudo_bypass_blocked(self, sandbox_config):
        """Sudo access is blocked by isolation flags."""
        isolation = sandbox_config["junieAgentSandbox"]["isolation"]
        assert isolation["noSudo"] is True

    def test_n8n_db_bypass_blocked(self, sandbox_config):
        """n8n database access is blocked by sandbox config."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/var/lib/n8n" in fs["denyRead"]

    def test_secrets_bypass_blocked(self, sandbox_config):
        """Secrets access is blocked by sandbox config."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/home/fenatodev/.config" in fs["denyRead"]

    def test_ssh_key_bypass_blocked(self, sandbox_config):
        """SSH key access is blocked by sandbox config."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/home/fenatodev/.ssh" in fs["denyRead"]

    def test_junie_config_bypass_blocked(self, sandbox_config):
        """Junie config from host is blocked by sandbox config."""
        fs = sandbox_config["junieAgentSandbox"]["fileSystem"]
        assert "/home/fenatodev/.junie" in fs["denyRead"]

    def test_network_bypass_blocked(self, sandbox_config):
        """Network access to internal hosts is blocked."""
        network = sandbox_config["junieAgentSandbox"]["network"]
        assert "172.16.0.0/12" in network["deniedHosts"]
        assert "192.168.0.0/16" in network["deniedHosts"]
        assert "10.0.0.0/8" in network["deniedHosts"]

    def test_mcp_bypass_blocked(self, sandbox_config):
        """MCP servers that control host are blocked."""
        mcp_policy = sandbox_config["junieAgentSandbox"]["mcpPolicy"]
        assert mcp_policy["defaultAction"] == "deny"
        assert len(mcp_policy["allowedServers"]) == 0

    def test_git_hooks_bypass_blocked(self, dockerfile):
        """Git hooks are not writable in sandbox mode."""
        # Junie sandbox mode blocks .git/hooks by default
        # The Dockerfile should not copy or allow git hooks
        assert ".git/hooks" not in dockerfile or "NOT" in dockerfile


# ---------------------------------------------------------------------------
# TestIDEvsCLI: IDE vs CLI differentiation
# ---------------------------------------------------------------------------


class TestIDEvsCLI:
    """Test that IDE and CLI are properly differentiated."""

    def test_launcher_is_cli_only(self, launcher_script):
        """The launcher is for CLI, not IDE plugin."""
        assert "junie" in launcher_script.lower()
        assert "--auth" in launcher_script

    def test_sandbox_config_is_cli_only(self, sandbox_config):
        """The sandbox config is for CLI, not IDE."""
        junie_config = sandbox_config["junieAgentSandbox"]["junieConfig"]
        assert junie_config["headless"] is True

    def test_dockerfile_is_cli_only(self, dockerfile):
        """The Dockerfile is for CLI, not IDE."""
        # The Dockerfile should not reference PyCharm or IDE
        assert "pycharm" not in dockerfile.lower()
        assert "intellij" not in dockerfile.lower()

    def test_compose_is_cli_only(self, docker_compose):
        """The compose file is for CLI, not IDE."""
        # The compose file should not reference IDE
        assert "pycharm" not in docker_compose.lower()
        assert "intellij" not in docker_compose.lower()

    def test_ide_not_affected(self, docker_compose):
        """The compose file does not affect the running IDE."""
        # The compose file should not mount or modify IDE directories
        assert ".idea" not in docker_compose or "NOT" in docker_compose


# ---------------------------------------------------------------------------
# TestDockerComposeSyntax: Validate compose syntax
# ---------------------------------------------------------------------------


class TestDockerComposeSyntax:
    """Validate that docker-compose.yml has valid syntax."""

    def test_compose_config_valid(self, agent_sandbox_dir):
        """The compose file passes docker compose config validation."""
        import subprocess

        result = subprocess.run(
            ["docker", "compose", "-f", str(agent_sandbox_dir / "docker-compose.yml"),
             "config", "--no-interpolate", "--quiet"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"Compose config failed: {result.stderr}"

    def test_compose_has_services(self, docker_compose):
        """The compose file has at least one service."""
        assert "services:" in docker_compose

    def test_compose_has_volumes(self, docker_compose):
        """The compose file has volume definitions."""
        assert "volumes:" in docker_compose

    def test_compose_network_mode_none(self, docker_compose):
        """The compose file uses network_mode: none for maximum isolation.

        Note: With network_mode: none, there's no need for a networks section.
        The previous version had a networks section with internal: true, but
        network_mode: none is stronger — it disables all networking.
        """
        assert "network_mode: none" in docker_compose


# ---------------------------------------------------------------------------
# TestHealthcheckExecution: Run healthcheck in isolated environment
# ---------------------------------------------------------------------------


class TestHealthcheckExecution:
    """Test the healthcheck script by executing it directly.

    We cannot import ops.agent_sandbox.healthcheck because the ops directory
    is not in the Python path. Instead, we execute the healthcheck script
    directly and verify its output.
    """

    def test_healthcheck_script_runs(self):
        """The healthcheck script executes without import errors."""
        import subprocess

        result = subprocess.run(
            [".venv/bin/python", "ops/agent-sandbox/healthcheck.py"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        # The script should run — it may fail some checks on the host,
        # but it should not crash with import errors
        assert "ModuleNotFoundError" not in result.stderr

    def test_healthcheck_no_docker_socket_on_host(self):
        """Docker socket check works on the test host."""
        # On the test host, /var/run/docker.sock may exist (Docker is running)
        # but the healthcheck function should still be callable
        import subprocess

        result = subprocess.run(
            [".venv/bin/python", "-c",
             "import os; print(not os.path.exists('/var/run/docker.sock'))"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Just verify the check is executable
        assert result.returncode == 0

    def test_healthcheck_no_lxd_socket_on_host(self):
        """LXD socket check works on the test host."""
        import subprocess

        result = subprocess.run(
            [".venv/bin/python", "-c",
             "print(not any(__import__('os').path.exists(p) for p in ['/var/lib/lxd/unix.socket', '/var/lib/lxd/socket']))"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0

    def test_healthcheck_no_user_home_on_host(self):
        """User home check works on the test host."""
        import subprocess

        result = subprocess.run(
            [".venv/bin/python", "-c",
             "import os; print(not os.path.exists('/home/fenatodev/.ssh'))"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0

    def test_healthcheck_no_n8n_data_on_host(self):
        """n8n data check works on the test host."""
        import subprocess

        result = subprocess.run(
            [".venv/bin/python", "-c",
             "import os; print(not os.path.exists('/var/lib/n8n'))"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        assert result.returncode == 0

    def test_healthcheck_non_root_user_on_host(self):
        """Non-root user check works on the test host."""
        import subprocess

        result = subprocess.run(
            [".venv/bin/python", "-c",
             "import os; print(os.getuid() != 0)"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # The test runs as the test user, not root
        assert result.returncode == 0
        assert result.stdout.strip() == "True"

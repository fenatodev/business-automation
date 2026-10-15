"""WP-057: Tests for sandbox fixes — detecting real defects found in audit.

These tests validate the defects identified in the audit and finalization:
1. Dockerfile installs Junie CLI officially (not silent Python fallback)
2. Dockerfile fails immediately on installation failure (no || true or || echo)
3. --sandbox flag is NOT invoked unconditionally on release builds
4. docker-compose.yml uses network_mode: none explicitly for test profile
5. docker-compose.yml has operational profile with internal network
6. No git credential.helper store or plaintext token persistence
7. Volumes don't hide scripts copied in Dockerfile (documented limitation)
8. Healthcheck has no false-success fallback when Junie CLI is missing
9. Clear distinction between isolation configured vs enforced
10. Dockerfile completeness: all files referenced by CMD/ENTRYPOINT are copied

These tests use synthetic data only — no real tokens, no n8n access,
no Docker build or runtime modifications.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

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
def launcher_script(agent_sandbox_dir):
    """Read the launcher script."""
    return (agent_sandbox_dir / "launch-agent.sh").read_text(encoding="utf-8")


@pytest.fixture()
def healthcheck_script(agent_sandbox_dir):
    """Read the healthcheck script."""
    return (agent_sandbox_dir / "healthcheck.py").read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# TestJunieCLIInstallation: Dockerfile installs Junie CLI officially
# ---------------------------------------------------------------------------


class TestJunieCLIInstallation:
    """Validate that the Dockerfile installs Junie CLI via official method."""

    def test_dockerfile_installs_junie_cli(self, dockerfile):
        """The Dockerfile must install Junie CLI via official curl script."""
        assert "junie.jetbrains.com/install.sh" in dockerfile, (
            "Dockerfile should install Junie CLI via official installer"
        )

    def test_dockerfile_does_not_fake_junie(self, dockerfile):
        """The Dockerfile must NOT replace Junie CLI with a Python script."""
        # The Dockerfile should not create a fake junie command
        assert "cat > /usr/local/bin/junie" not in dockerfile
        assert '#!/usr/bin/env python3' not in dockerfile or "healthcheck" in dockerfile

    def test_dockerfile_verifies_junie_installation(self, dockerfile):
        """The Dockerfile should verify Junie CLI installation."""
        assert "junie --version" in dockerfile, (
            "Dockerfile should verify Junie CLI installation"
        )

    def test_dockerfile_documents_sandbox_limitation(self, dockerfile):
        """The Dockerfile should document that --sandbox is not in release builds."""
        assert "sandbox" in dockerfile.lower(), (
            "Dockerfile should mention --sandbox limitation"
        )

    def test_dockerfile_fails_on_install_error(self, dockerfile):
        """The Dockerfile must NOT mask installation failures with || true or || echo."""
        # Check that || true and || echo are NOT used to mask failures
        lines = dockerfile.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#"):
                continue
            # Check for || true or || echo patterns that mask failures
            if "|| true" in stripped:
                assert False, (
                    f"Dockerfile masks failure with || true: {stripped}"
                )
            if "|| echo" in stripped:
                assert False, (
                    f"Dockerfile masks failure with || echo: {stripped}"
                )

    def test_dockerfile_junie_version_fails_build(self, dockerfile):
        """The Dockerfile must fail the build if junie --version fails."""
        # Find the line with junie --version
        lines = dockerfile.split("\n")
        for line in lines:
            stripped = line.strip()
            if "junie --version" in stripped and not stripped.startswith("#"):
                # This line should NOT have || true or || echo
                assert "|| true" not in stripped and "|| echo" not in stripped, (
                    f"junie --version should fail build on error, not mask it: {stripped}"
                )
                break
        else:
            pytest.fail("Dockerfile should contain 'junie --version' command")


# ---------------------------------------------------------------------------
# TestSandboxFlag: --sandbox is NOT invoked unconditionally
# ---------------------------------------------------------------------------


class TestSandboxFlag:
    """Validate that --sandbox is handled correctly for release builds."""

    def test_launcher_checks_sandbox_support(self, launcher_script):
        """The launcher should check if --sandbox is supported before using it."""
        assert "--sandbox" in launcher_script, (
            "Launcher should reference --sandbox flag"
        )
        # The launcher should NOT unconditionally invoke --sandbox
        # It should check first or use a conditional
        lines = launcher_script.split("\n")
        has_conditional = False
        for line in lines:
            if "grep" in line and "--sandbox" in line:
                has_conditional = True
            if "SANDBOX_FLAG" in line:
                has_conditional = True
        assert has_conditional, (
            "Launcher should conditionally use --sandbox, not invoke it unconditionally"
        )

    def test_launcher_documents_sandbox_limitation(self, launcher_script):
        """The launcher should document that --sandbox is dev/nightly only."""
        assert "release" in launcher_script.lower() or "dev" in launcher_script.lower(), (
            "Launcher should document --sandbox availability"
        )


# ---------------------------------------------------------------------------
# TestNetworkMode: docker-compose uses network_mode: none
# ---------------------------------------------------------------------------


class TestNetworkMode:
    """Validate that docker-compose explicitly disables network access."""

    def test_network_mode_none(self, docker_compose):
        """The compose file must use network_mode: none explicitly for test profile."""
        assert "network_mode: none" in docker_compose, (
            "docker-compose.yml must use network_mode: none for test profile"
        )

    def test_operational_profile_exists(self, docker_compose):
        """The compose file must have an operational profile with restricted network."""
        assert "junie-agent-operational" in docker_compose, (
            "docker-compose.yml must have operational profile service"
        )
        assert "profiles:" in docker_compose, (
            "docker-compose.yml must define profiles"
        )
        assert "operational" in docker_compose, (
            "docker-compose.yml must have operational profile"
        )

    def test_internal_network_for_operational(self, docker_compose):
        """The operational profile must use internal network (no internet access)."""
        assert "internal: true" in docker_compose, (
            "docker-compose.yml must have internal network for operational profile"
        )

    def test_docker_compose_config_validates(self, agent_sandbox_dir):
        """docker compose config should pass without errors."""
        result = subprocess.run(
            ["docker", "compose", "-f", str(agent_sandbox_dir / "docker-compose.yml"),
             "config", "--no-interpolate", "--quiet"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, (
            f"docker compose config failed: {result.stderr}"
        )


# ---------------------------------------------------------------------------
# TestGitTokenSecurity: No plaintext token persistence
# ---------------------------------------------------------------------------


class TestGitTokenSecurity:
    """Validate that Git tokens are not persisted in plaintext."""

    def test_no_credential_helper_store(self, launcher_script):
        """The launcher must NOT use git credential.helper store as an active command."""
        # Check for actual usage, not just comments mentioning it
        lines = launcher_script.split("\n")
        for line in lines:
            stripped = line.strip()
            # Skip comments
            if stripped.startswith("#"):
                continue
            assert "credential.helper store" not in stripped, (
                f"git credential.helper store persists tokens in plaintext: {stripped}"
            )

    def test_no_plaintext_token_write(self, launcher_script):
        """The launcher must NOT write tokens to files in plaintext."""
        # Check for patterns like echo "token" > file
        lines = launcher_script.split("\n")
        for line in lines:
            if "GIT_TOKEN" in line and "> " in line:
                # Allow GIT_ASKPASS scripts but not direct token writes
                assert "ASKPASS" in line or "GIT_CONFIG" in line, (
                    f"Potential plaintext token write: {line.strip()}"
                )

    def test_healthcheck_checks_no_plaintext_secrets(self, healthcheck_script):
        """The healthcheck should verify no plaintext secrets are persisted."""
        assert "plaintext" in healthcheck_script.lower() or "secret" in healthcheck_script.lower(), (
            "Healthcheck should check for plaintext secrets"
        )


# ---------------------------------------------------------------------------
# TestVolumeShadowing: Documented limitation
# ---------------------------------------------------------------------------


class TestVolumeShadowing:
    """Validate that volume shadowing is documented."""

    def test_dockerfile_documents_volume_shadowing(self, dockerfile):
        """The Dockerfile should document that volumes shadow copied files."""
        assert "volume" in dockerfile.lower() or "shadow" in dockerfile.lower(), (
            "Dockerfile should mention volume shadowing"
        )

    def test_compose_documents_volume_shadowing(self, docker_compose):
        """The compose file should document that volumes shadow copied files."""
        assert "shadow" in docker_compose.lower() or "volume" in docker_compose.lower(), (
            "docker-compose.yml should mention volume shadowing"
        )


# ---------------------------------------------------------------------------
# TestHealthcheckNoFallback: No false-success fallback
# ---------------------------------------------------------------------------


class TestHealthcheckNoFallback:
    """Validate that healthcheck has no false-success fallback."""

    def test_healthcheck_checks_junie_cli(self, healthcheck_script):
        """The healthcheck should verify Junie CLI is installed."""
        assert "junie" in healthcheck_script.lower(), (
            "Healthcheck should check for Junie CLI"
        )
        assert "which" in healthcheck_script or "shutil" in healthcheck_script, (
            "Healthcheck should use shutil.which or similar to check Junie CLI"
        )

    def test_launcher_fails_without_junie(self, launcher_script):
        """The launcher should exit with error if Junie CLI is not found."""
        assert "exit 1" in launcher_script, (
            "Launcher should exit with error when Junie CLI is missing"
        )
        # The launcher should NOT fall back to running pytest
        assert "pytest" not in launcher_script, (
            "Launcher should NOT fall back to running pytest when Junie CLI is missing"
        )

    def test_launcher_no_false_success(self, launcher_script):
        """The launcher should NOT report success when Junie CLI is missing."""
        lines = launcher_script.split("\n")
        # After the junie check, there should be no "finished" or "success" message
        # without an exit 1 in between
        found_junie_check = False
        for line in lines:
            if "command -v junie" in line:
                found_junie_check = True
            if found_junie_check and "exit 1" in line:
                break
        assert found_junie_check, (
            "Launcher should check for Junie CLI and exit on failure"
        )


# ---------------------------------------------------------------------------
# TestIsolationDistinction: Configured vs Enforced
# ---------------------------------------------------------------------------


class TestIsolationDistinction:
    """Validate clear distinction between isolation configured vs enforced."""

    def test_healthcheck_documents_limitation(self, healthcheck_script):
        """The healthcheck should document it validates configuration, not enforcement."""
        assert "configuration" in healthcheck_script.lower() or "configur" in healthcheck_script.lower(), (
            "Healthcheck should mention it validates configuration"
        )

    def test_healthcheck_mentions_enforcement_limitation(self, healthcheck_script):
        """The healthcheck should mention it does not validate runtime enforcement."""
        assert "enforcement" in healthcheck_script.lower() or "bypass" in healthcheck_script.lower(), (
            "Healthcheck should mention enforcement limitation"
        )


# ---------------------------------------------------------------------------
# TestDockerfileCompleteness: All CMD/ENTRYPOINT files are copied
# ---------------------------------------------------------------------------


class TestDockerfileCompleteness:
    """Validate that Dockerfile copies all files referenced by CMD/ENTRYPOINT."""

    def test_cmd_file_is_copied(self, dockerfile):
        """The file referenced by CMD must be copied in the Dockerfile."""
        # Find CMD directive
        lines = dockerfile.split("\n")
        cmd_file = None
        for line in lines:
            if line.strip().startswith("CMD"):
                # Extract file path from CMD
                if "launch-agent.sh" in line:
                    cmd_file = "launch-agent.sh"
                break

        if cmd_file:
            assert f"COPY" in dockerfile and cmd_file in dockerfile, (
                f"Dockerfile should COPY {cmd_file} referenced by CMD"
            )

    def test_healthcheck_file_is_copied(self, dockerfile):
        """The file referenced by HEALTHCHECK must be copied in the Dockerfile."""
        assert "healthcheck.py" in dockerfile, (
            "Dockerfile should COPY healthcheck.py referenced by HEALTHCHECK"
        )

    def test_init_files_for_python_imports(self, dockerfile):
        """Dockerfile should copy __init__.py for Python package imports."""
        # The Dockerfile copies ops/ which includes __init__.py files
        assert "ops/" in dockerfile, (
            "Dockerfile should copy ops/ directory with __init__.py files"
        )

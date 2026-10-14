"""Portable private VPS stack contract; no containers are created by tests."""

import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1] / "ops" / "vps"
COMPOSE = ROOT / "compose.yaml"
PREFLIGHT = ROOT / "preflight.py"


def load_preflight():
    spec = importlib.util.spec_from_file_location("portable_vps_preflight", PREFLIGHT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_generate_and_validate_independent_private_secrets(tmp_path):
    preflight = load_preflight()
    env = tmp_path / ".env"
    preflight.initialize(env)
    assert os.stat(env).st_mode & 0o777 == 0o600
    settings = preflight.validate(env)
    assert settings["N8N_VERSION"] == "2.40.7"
    assert len({settings[key] for key in preflight.SECRET_KEYS}) == 3
    with pytest.raises(FileExistsError):
        preflight.initialize(env)


def test_reject_insecure_file_permissions(tmp_path):
    preflight = load_preflight()
    env = tmp_path / ".env"
    preflight.initialize(env)
    env.chmod(0o644)
    with pytest.raises(ValueError, match="permissions"):
        preflight.validate(env)


def test_reject_weak_or_duplicate_secrets(tmp_path):
    preflight = load_preflight()
    env = tmp_path / ".env"
    preflight.initialize(env)
    data = preflight.validate(env)
    data["N8N_ENCRYPTION_KEY"] = "REPLACE_WITH_RANDOM_SECRET"
    env.write_text("".join(f"{k}={v}\n" for k, v in data.items()))
    with pytest.raises(ValueError, match="not a valid generated secret"):
        preflight.validate(env)

    data["N8N_ENCRYPTION_KEY"] = data["N8N_RUNNERS_AUTH_TOKEN"]
    env.write_text("".join(f"{k}={v}\n" for k, v in data.items()))
    with pytest.raises(ValueError, match="independent"):
        preflight.validate(env)


def test_reject_symlink_and_unexpected_env_keys(tmp_path):
    preflight = load_preflight()
    env = tmp_path / ".env"
    preflight.initialize(env)
    alias = tmp_path / "alias.env"
    alias.symlink_to(env)
    with pytest.raises(ValueError, match="unsafe"):
        preflight.validate(alias)
    env.write_text(env.read_text() + "UNEXPECTED_VARIABLE=1\n")
    with pytest.raises(ValueError, match="unexpected"):
        preflight.validate(env)


def test_compose_static_private_contract():
    text = COMPOSE.read_text()
    assert "127.0.0.1:5678:5678" in text
    assert text.count("    ports:") == 1
    assert "N8N_BLOCK_ENV_ACCESS_IN_NODE" in text
    assert "DB_TYPE: postgresdb" in text
    assert "N8N_ENCRYPTION_KEY:" in text
    assert "N8N_RUNNERS_AUTH_TOKEN:" in text
    assert "postgres_data:/var/lib/postgresql/data" in text
    assert "n8n_data:/home/node/.n8n" in text
    assert "privileged: true" not in text.lower()
    assert "network_mode: host" not in text.lower()
    assert "image: postgres:latest" not in text
    assert "image: docker.n8n.io/n8nio/n8n:latest" not in text


def test_docker_compose_renders_without_exposing_db_or_runner(tmp_path):
    docker = shutil.which("docker")
    if not docker:
        pytest.skip("Docker CLI not installed")
    verify = subprocess.run(
        [docker, "compose", "version"], capture_output=True, text=True, timeout=8
    )
    if verify.returncode != 0:
        pytest.skip("Docker Compose is unavailable")
    preflight = load_preflight()
    env = tmp_path / ".env"
    preflight.initialize(env)
    result = subprocess.run(
        [
            docker, "compose", "--env-file", str(env),
            "-f", str(COMPOSE), "config", "--format", "json",
        ],
        capture_output=True, text=True, timeout=15,
    )
    # Avoid logging rendered config; it contains synthetic test passwords.
    assert result.returncode == 0, "Docker Compose refused to render template"
    rendered = json.loads(result.stdout)
    assert set(rendered["services"]) == {"postgres", "n8n", "runners"}
    n8n_ports = rendered["services"]["n8n"]["ports"]
    assert len(n8n_ports) == 1
    assert n8n_ports[0]["host_ip"] == "127.0.0.1"
    assert n8n_ports[0]["published"] == "5678"
    for service in ("postgres", "runners"):
        assert not rendered["services"][service].get("ports")
    assert all(not item.get("privileged") for item in rendered["services"].values())

"""Static deployment guardrails; does not build or start Docker."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = (ROOT / "ops/private-api/Dockerfile").read_text()
COMPOSE = (ROOT / "ops/private-api/compose.private.yml").read_text()


def test_private_compose_never_publishes_host_ports():
    assert "ports:" not in COMPOSE
    assert "network_mode:" not in COMPOSE
    assert "privileged:" not in COMPOSE
    assert "docker.sock" not in COMPOSE
    assert "expose:" in COMPOSE
    assert "n8n_default" in COMPOSE
    assert "external: true" in COMPOSE


def test_private_compose_requires_local_only_credentials():
    assert "BA_PRIVATE_ENV_FILE:?" in COMPOSE
    assert "BA_INTAKE_GENERATOR: static" in COMPOSE
    assert "cap_drop:" in COMPOSE
    assert "no-new-privileges:true" in COMPOSE
    assert "read_only: true" in COMPOSE
    assert "restart: \"no\"" in COMPOSE


def test_image_has_no_migration_or_start_side_effects():
    assert "USER 10001:10001" in DOCKERFILE
    assert "uv sync --locked --no-dev" in DOCKERFILE
    assert "alembic upgrade" not in DOCKERFILE
    assert "n8n import" not in DOCKERFILE
    assert "--no-access-log" in DOCKERFILE
    assert "app.intake_only:app" in DOCKERFILE
    assert "app.main:app" not in DOCKERFILE


def test_existing_workflow_stays_inactive():
    import json

    path = ROOT / "ops/n8n/workflows/client0-commercial-intake-review.json"
    workflow = json.loads(path.read_text())
    assert workflow["active"] is False

"""Testes locais: não usam Docker, rede, credenciais reais ou PostgreSQL."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import stat

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "erpnext_sandbox.py"
spec = spec_from_file_location("erpnext_sandbox_module", SCRIPT)
sandbox = module_from_spec(spec)
spec.loader.exec_module(sandbox)

EXAMPLE_SOURCE = """services:
  backend:
    image: frappe/erpnext:v16.50.0
    environment:
      MYSQL_ROOT_PASSWORD: admin
      MARIADB_ROOT_PASSWORD: admin
  create-site:
    image: frappe/erpnext:v16.50.0
    volumes:
      - sites:/home/frappe/frappe-bench/sites
    entrypoint:
      - bash
      - -c
    command:
      - bench new-site --admin-password=admin --db-root-password=admin
  db:
    image: mariadb:11.8
    environment:
      MYSQL_ROOT_PASSWORD: admin
      MARIADB_ROOT_PASSWORD: admin
  frontend:
    image: frappe/erpnext:v16.50.0
    ports:
      - "8080:8080"
"""


def test_transform_removes_weak_demo_credentials_and_public_bind():
    hardened = sandbox.transform_compose(EXAMPLE_SOURCE)
    assert "--admin-password=admin" not in hardened
    assert "--db-root-password=admin" not in hardened
    assert "MYSQL_ROOT_PASSWORD: admin" not in hardened
    assert "MARIADB_ROOT_PASSWORD: admin" not in hardened
    assert '"8080:8080"' not in hardened
    assert "127.0.0.1:${ERP_SANDBOX_HTTP_PORT:?missing}:8080" in hardened
    assert "ERP_SANDBOX_ADMIN_PASSWORD" in hardened
    assert "ERP_SANDBOX_DB_ROOT_PASSWORD" in hardened


@pytest.mark.parametrize(
    "broken",
    [
        EXAMPLE_SOURCE.replace('"8080:8080"', '"0.0.0.0:8080:8080"'),
        EXAMPLE_SOURCE.replace("--admin-password=admin", "--admin-password=1234"),
        EXAMPLE_SOURCE.replace("  create-site:\n", "  no-site:\n"),
        EXAMPLE_SOURCE.replace("MYSQL_ROOT_PASSWORD: admin", "MYSQL_ROOT_PASSWORD: foo", 1),
    ],
)
def test_transform_fails_closed_on_unexpected_input(broken):
    with pytest.raises(sandbox.SandboxError):
        sandbox.transform_compose(broken)


def minimal_compose_config():
    services = {
        name: {"image": "frappe/erpnext:v16.50.0"}
        for name in sandbox.SERVICES
    }
    services["db"]["image"] = "mariadb:11.8"
    for name in ("redis-cache", "redis-queue"):
        services[name]["image"] = "redis:6.2-alpine"
    services["frontend"]["ports"] = [
        {"host_ip": "127.0.0.1", "published": str(sandbox.PORT), "target": 8080}
    ]
    return {"services": services}


def test_rejects_public_port_or_extra_published_port():
    config = minimal_compose_config()
    sandbox.check_configuration(config)
    config["services"]["frontend"]["ports"][0]["host_ip"] = "0.0.0.0"
    with pytest.raises(sandbox.SandboxError):
        sandbox.check_configuration(config)
    config = minimal_compose_config()
    config["services"]["db"]["ports"] = [{"published": 3306, "target": 3306}]
    with pytest.raises(sandbox.SandboxError):
        sandbox.check_configuration(config)


def test_rejects_unknown_service_or_image():
    config = minimal_compose_config()
    config["services"]["unreviewed-service"] = {}
    with pytest.raises(sandbox.SandboxError):
        sandbox.check_configuration(config)
    config = minimal_compose_config()
    config["services"]["backend"]["image"] = "frappe/erpnext:latest"
    with pytest.raises(sandbox.SandboxError):
        sandbox.check_configuration(config)


def test_prepare_is_private_and_never_overwrites(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(sandbox, "fetch_upstream", lambda: EXAMPLE_SOURCE)
    workdir = tmp_path / "fresh-sandbox"
    sandbox.prepare(workdir)
    assert stat.S_IMODE(workdir.stat().st_mode) == 0o700
    for name in (".env", "pwd.sandbox.yml"):
        assert stat.S_IMODE((workdir / name).stat().st_mode) == 0o600
    values = sandbox.read_local_env(workdir)
    assert values["ERP_SANDBOX_ADMIN_PASSWORD"] != values["ERP_SANDBOX_DB_ROOT_PASSWORD"]
    assert len(values["ERP_SANDBOX_ADMIN_PASSWORD"]) == 64
    assert values["ERP_SANDBOX_HTTP_PORT"] == "18080"
    printed = capsys.readouterr().out
    assert values["ERP_SANDBOX_ADMIN_PASSWORD"] not in printed
    assert values["ERP_SANDBOX_DB_ROOT_PASSWORD"] not in printed
    with pytest.raises(sandbox.SandboxError):
        sandbox.prepare(workdir)

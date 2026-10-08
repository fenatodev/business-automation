#!/usr/bin/env python3
"""ERPNext sandbox descartável e independente do runtime Business Automation.

Comandos explícitos: prepare, validate, start, status, smoke e stop.
Nunca usa .env do BA, PostgreSQL do BA, nem remove volumes automaticamente.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request


UPSTREAM_COMMIT = "5aa31a4aedf5caaf5abd46d94aada11e40d1709c"
UPSTREAM_URL = (
    "https://raw.githubusercontent.com/frappe/frappe_docker/"
    + UPSTREAM_COMMIT
    + "/pwd.yml"
)
UPSTREAM_SHA256 = "46f1a8f73b96556ff44c7bc61e59f7b3612f1e1c838f276577cbccb01e817122"
PROJECT = "baerpnextwp015"
PORT = 18080
WORKSPACE = Path.home() / ".local/share/business-automation/erpnext-sandbox"
SERVICES = {
    "backend", "configurator", "create-site", "db", "frontend",
    "queue-long", "queue-short", "redis-queue", "redis-cache",
    "scheduler", "websocket",
}


class SandboxError(RuntimeError):
    pass


def transform_compose(source: str) -> str:
    """Endurece exatamente o layout oficial fixado. Drift inesperado falha fechado."""
    changes = (
        ("MYSQL_ROOT_PASSWORD: admin", "MYSQL_ROOT_PASSWORD: ${ERP_SANDBOX_DB_ROOT_PASSWORD:?missing}", 2),
        ("MARIADB_ROOT_PASSWORD: admin", "MARIADB_ROOT_PASSWORD: ${ERP_SANDBOX_DB_ROOT_PASSWORD:?missing}", 2),
        ("--admin-password=admin", '--admin-password="$$ERP_SANDBOX_ADMIN_PASSWORD"', 1),
        ("--db-root-password=admin", '--db-root-password="$$ERP_SANDBOX_DB_ROOT_PASSWORD"', 1),
        ('"8080:8080"', '"127.0.0.1:${ERP_SANDBOX_HTTP_PORT:?missing}:8080"', 1),
    )
    for old, new, expected in changes:
        if source.count(old) != expected:
            raise SandboxError("Layout oficial inesperado; transformação recusada: " + old)
        source = source.replace(old, new)

    prefix, sep, remainder = source.partition("  create-site:\n")
    if not sep:
        raise SandboxError("Serviço create-site ausente")
    section, sep, suffix = remainder.partition("  db:\n")
    if not sep or section.count("    entrypoint:\n") != 1:
        raise SandboxError("Layout create-site alterado")
    injection = (
        "    environment:\n"
        "      ERP_SANDBOX_ADMIN_PASSWORD: ${ERP_SANDBOX_ADMIN_PASSWORD:?missing}\n"
        "      ERP_SANDBOX_DB_ROOT_PASSWORD: ${ERP_SANDBOX_DB_ROOT_PASSWORD:?missing}\n"
        "    entrypoint:\n"
    )
    section = section.replace("    entrypoint:\n", injection, 1)
    source = prefix + "  create-site:\n" + section + "  db:\n" + suffix
    if "--admin-password=admin" in source or '--db-root-password=admin' in source:
        raise SandboxError("Credenciais fixas ainda presentes")
    return source


def ensure_private_directory(path: Path) -> None:
    if path.is_symlink():
        raise SandboxError("Diretório de sandbox não pode ser symlink")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise SandboxError("Sandbox deve ser privado (chmod 700)")


def write_private_new(path: Path, content: str) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(content)


def fetch_upstream() -> str:
    request = urllib.request.Request(
        UPSTREAM_URL, headers={"User-Agent": "business-automation-erpnext-sandbox/1"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(100_000)
        if response.read(1):
            raise SandboxError("Arquivo oficial inesperadamente grande")
    if hashlib.sha256(data).hexdigest() != UPSTREAM_SHA256:
        raise SandboxError("SHA-256 do compose oficial divergente; nada será iniciado")
    return data.decode("utf-8")


def prepare(path: Path) -> None:
    ensure_private_directory(path)
    compose = path / "pwd.sandbox.yml"
    env = path / ".env"
    if compose.exists() or env.exists() or compose.is_symlink() or env.is_symlink():
        raise SandboxError("Sandbox já existe ou incompleto; preservar estado e inspecionar")
    source = fetch_upstream()
    hardened = transform_compose(source)
    credentials = (
        "ERP_SANDBOX_ADMIN_PASSWORD=" + secrets.token_hex(32) + "\n"
        "ERP_SANDBOX_DB_ROOT_PASSWORD=" + secrets.token_hex(32) + "\n"
        "ERP_SANDBOX_HTTP_PORT=" + str(PORT) + "\n"
    )
    # Credenciais são criadas somente no host, fora do repositório público.
    write_private_new(env, credentials)
    write_private_new(compose, hardened)
    print("PREPARED=PASS")
    print("Private location: " + str(path))
    print("ERPNext será acessível apenas em http://127.0.0.1:" + str(PORT))
    print("Nenhum container iniciado; credenciais não foram exibidas.")


def read_local_env(path: Path) -> dict[str, str]:
    env = path / ".env"
    compose = path / "pwd.sandbox.yml"
    for item in (env, compose):
        if item.is_symlink() or not item.is_file() or stat.S_IMODE(item.stat().st_mode) & 0o077:
            raise SandboxError("Arquivo local ausente, symlink ou não privado: " + item.name)
    values = {}
    for line in env.read_text(encoding="utf-8").splitlines():
        if not line:
            continue
        key, sep, value = line.partition("=")
        if not sep or key in values:
            raise SandboxError("Configuração privada inválida")
        values[key] = value
    for key in ("ERP_SANDBOX_DB_ROOT_PASSWORD", "ERP_SANDBOX_ADMIN_PASSWORD"):
        if not re.fullmatch(r"[0-9a-f]{64}", values.get(key, "")):
            raise SandboxError("Credencial não aleatória ou inválida no sandbox")
    if values.get("ERP_SANDBOX_HTTP_PORT") != str(PORT):
        raise SandboxError("Porta inesperada no sandbox")
    return values


def compose_cmd(path: Path, *args: str) -> list[str]:
    return [
        "docker", "compose", "--project-name", PROJECT, "--env-file", str(path / ".env"),
        "-f", str(path / "pwd.sandbox.yml"), *args,
    ]


def check_configuration(data: dict, port: int = PORT) -> None:
    services = data.get("services", {})
    if set(services) != SERVICES:
        raise SandboxError("Serviços inesperados no Compose")
    frontend = services["frontend"]
    ports = frontend.get("ports", [])
    if len(ports) != 1 or (
        ports[0].get("host_ip") != "127.0.0.1"
        or str(ports[0].get("published")) != str(port)
        or int(ports[0].get("target", 0)) != 8080
    ):
        raise SandboxError("Publicação HTTP não isolada em loopback")
    if any(details.get("ports") for name, details in services.items() if name != "frontend"):
        raise SandboxError("Outra porta publicada no host")
    if services["db"].get("image") != "mariadb:11.8":
        raise SandboxError("Banco ERP inesperado")
    for details in services.values():
        image = details.get("image")
        if image and image not in {
            "mariadb:11.8", "redis:6.2-alpine", "frappe/erpnext:v16.50.0"
        }:
            raise SandboxError("Imagem não prevista no Compose")


def validate(path: Path) -> None:
    ensure_private_directory(path)
    values = read_local_env(path)
    if not shutil.which("docker"):
        raise SandboxError("Docker não disponível")
    raw = subprocess.run(
        compose_cmd(path, "config", "--format", "json"),
        capture_output=True, text=True, check=True,
    )
    # Nunca imprimir o JSON do Compose: ele contém secrets interpolados.
    data = json.loads(raw.stdout)
    check_configuration(data, port=int(values["ERP_SANDBOX_HTTP_PORT"]))
    env_db = data["services"]["db"]["environment"]
    env_site = data["services"]["create-site"]["environment"]
    if env_db.get("MARIADB_ROOT_PASSWORD") != values["ERP_SANDBOX_DB_ROOT_PASSWORD"]:
        raise SandboxError("Senha do MariaDB divergente da configuração privada")
    if env_site.get("ERP_SANDBOX_ADMIN_PASSWORD") != values["ERP_SANDBOX_ADMIN_PASSWORD"]:
        raise SandboxError("Senha do site divergente da configuração privada")
    if env_site.get("ERP_SANDBOX_DB_ROOT_PASSWORD") != values["ERP_SANDBOX_DB_ROOT_PASSWORD"]:
        raise SandboxError("Senha do bootstrap divergente da configuração privada")
    print("CONFIG_VALIDATION=PASS: imagens fixas, credenciais privadas, porta loopback")
    print("PostgreSQL do Business Automation não é referenciado")


def check_resources(path: Path) -> None:
    mem_kib = None
    with open("/proc/meminfo", encoding="utf-8") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                mem_kib = int(line.split()[1])
                break
    if mem_kib is None or mem_kib < 6 * 1024 * 1024:
        raise SandboxError("Menos de 6 GiB de RAM disponível; evitar sobrecarga")
    cores = os.cpu_count() or 1
    if os.getloadavg()[0] > cores * 0.8:
        raise SandboxError("Host com carga elevada; não iniciar ERPNext agora")
    free_bytes = shutil.disk_usage(path).free
    if free_bytes < 12 * 1024 ** 3:
        raise SandboxError("Menos de 12 GiB livres; evitar instalação incompleta")


def run_compose(path: Path, *args: str) -> None:
    # Evita downloads/extracoes paralelos que sobrecarregam o desktop.
    env = os.environ.copy()
    env["COMPOSE_PARALLEL_LIMIT"] = "1"
    subprocess.run(compose_cmd(path, *args), check=True, env=env)


def smoke(path: Path) -> None:
    import urllib.error
    url = "http://127.0.0.1:" + str(PORT) + "/login"
    try:
        with urllib.request.urlopen(url, timeout=8) as response:
            code = response.status
    except (urllib.error.URLError, TimeoutError) as exc:
        raise SandboxError("ERPNext ainda indisponível (verificar create-site/status)") from exc
    if code != 200:
        raise SandboxError("HTTP inesperado: " + str(code))
    print("ERP_HTTP=200; este smoke não valida configuração funcional do ERP")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "validate", "start", "status", "smoke", "stop"))
    args = parser.parse_args()
    try:
        if args.action == "prepare":
            prepare(WORKSPACE)
        elif args.action == "validate":
            validate(WORKSPACE)
        elif args.action == "start":
            validate(WORKSPACE)
            check_resources(WORKSPACE)
            run_compose(WORKSPACE, "up", "-d", "--quiet-pull")
            print("START_SUBMITTED: criação de site pode continuar em create-site")
        elif args.action == "status":
            validate(WORKSPACE)
            run_compose(WORKSPACE, "ps", "-a")
        elif args.action == "smoke":
            validate(WORKSPACE)
            smoke(WORKSPACE)
        elif args.action == "stop":
            validate(WORKSPACE)
            run_compose(WORKSPACE, "stop")
            print("STOP=PASS: volumes do sandbox preservados")
        return 0
    except (SandboxError, OSError, subprocess.CalledProcessError, urllib.error.URLError) as exc:
        print("SANDBOX_ERROR: " + str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

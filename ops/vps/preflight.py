"""Generate and verify a private .env for the portable F2 VPS stack.

No connections, installations, or containers are started by this script.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import secrets
import sys


DEFAULT_ENV = Path(__file__).resolve().parent / ".env"
EXPECTED_KEYS = {
    "COMPOSE_PROJECT_NAME",
    "N8N_VERSION",
    "N8N_DB_PASSWORD",
    "N8N_ENCRYPTION_KEY",
    "N8N_RUNNERS_AUTH_TOKEN",
}
SECRET_KEYS = ("N8N_DB_PASSWORD", "N8N_ENCRYPTION_KEY", "N8N_RUNNERS_AUTH_TOKEN")


def initialize(path: Path = DEFAULT_ENV) -> Path:
    """Create with exclusive mode 0600; never overwrite user configuration."""
    path.parent.mkdir(parents=True, exist_ok=True)
    values = {
        "COMPOSE_PROJECT_NAME": "ba-f2-pilot",
        "N8N_VERSION": "2.40.7",
        "N8N_DB_PASSWORD": secrets.token_urlsafe(48),
        "N8N_ENCRYPTION_KEY": secrets.token_hex(32),
        "N8N_RUNNERS_AUTH_TOKEN": secrets.token_urlsafe(48),
    }
    data = "".join(f"{k}={v}\n" for k, v in values.items())
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise
    return path


def validate(path: Path = DEFAULT_ENV) -> dict[str, str]:
    """Fail closed; do not print or return credentials to output."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("Missing or unsafe .env file")
    if path.stat().st_mode & 0o077:
        raise ValueError(".env permissions must be 0600")
    items: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise ValueError("Invalid .env line")
        name, value = line.split("=", 1)
        if not re.fullmatch(r"[A-Z][A-Z0-9_]*", name) or name in items:
            raise ValueError("Invalid or duplicate .env key")
        items[name] = value
    if set(items) != EXPECTED_KEYS:
        raise ValueError(".env has missing or unexpected keys")
    if not re.fullmatch(r"[a-z][a-z0-9-]{3,35}", items["COMPOSE_PROJECT_NAME"]):
        raise ValueError("Invalid Compose project identifier")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", items["N8N_VERSION"]):
        raise ValueError("Pin an exact n8n release version")
    for name in SECRET_KEYS:
        if (
            len(items[name]) < 40
            or "REPLACE" in items[name].upper()
            or any(char in items[name] for char in (" ", "\\", "'", '"', "$", "#"))
        ):
            raise ValueError(f"{name} is not a valid generated secret")
    if len({items[name] for name in SECRET_KEYS}) != len(SECRET_KEYS):
        raise ValueError("Secrets must be independent")
    return items


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("init", "check"))
    parser.add_argument("--env-file", type=Path, default=DEFAULT_ENV)
    args = parser.parse_args()
    try:
        if args.action == "init":
            initialize(args.env_file)
        validate(args.env_file)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"PRECHECK_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("F2_VPS_ENV_READY=YES (no containers started)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

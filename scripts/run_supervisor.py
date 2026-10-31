#!/usr/bin/env python
"""Standalone supervisor CLI for the internal task queue.

Runs `run_once()` continuously until SIGTERM/SIGINT.

Usage:
    uv run python scripts/run_supervisor.py

Environment:
    DATABASE_URL              — Required. PostgreSQL connection string.
    BA_INTAKE_SERVICE_CONTEXT — Optional. Service description (default from settings).
    BA_SUPERVISOR_INTERVAL    — Optional. Polling interval in seconds (default: 5).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path so that `app` is importable.
_project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_project_root))

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.services.supervisor import run


def main() -> None:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("ERROR: DATABASE_URL environment variable is required", file=sys.stderr)
        sys.exit(1)

    service_context = os.environ.get(
        "BA_INTAKE_SERVICE_CONTEXT",
        "Automação de processos e integrações sob diagnóstico.",
    )
    interval = float(os.environ.get("BA_SUPERVISOR_INTERVAL", "5"))

    engine = create_engine(database_url, pool_pre_ping=True)

    @event.listens_for(engine, "connect")
    def _sqlite_fk(dbapi_conn, _conn_record):
        # Only SQLite needs this; PostgreSQL ignores it harmlessly
        try:
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
        except Exception:
            pass

    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    print(f"Supervisor starting — interval: {interval}s, context: {service_context[:60]}...")

    try:
        stats = run(SessionLocal, service_context, interval=interval)
    except KeyboardInterrupt:
        pass

    print(
        f"Supervisor stopped — cycles: {stats.cycles}, "
        f"tasks: {stats.tasks_processed}, errors: {stats.errors}"
    )


if __name__ == "__main__":
    main()

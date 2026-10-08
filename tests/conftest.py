import hashlib
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ADMIN_TOKEN = "test-admin-token-not-a-real-secret"
OPERATOR_A_TOKEN = "test-operator-a-token-not-a-real-secret"
OPERATOR_B_TOKEN = "test-operator-b-token-not-a-real-secret"


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ["BA_ACCESS_IDENTITIES_JSON"] = json.dumps(
    [
        {
            "token_sha256": token_hash(ADMIN_TOKEN),
            "role": "admin",
        },
        {
            "token_sha256": token_hash(OPERATOR_A_TOKEN),
            "role": "operator",
            "company_id": 1,
        },
        {
            "token_sha256": token_hash(OPERATOR_B_TOKEN),
            "role": "operator",
            "company_id": 2,
        },
    ]
)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.main import app, get_db


engine = create_engine(
    os.environ["DATABASE_URL"],
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


@event.listens_for(engine, "connect")
def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


TestingSessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


@pytest.fixture(autouse=True)
def reset_database():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    def override_get_db():
        db = TestingSessionLocal()

        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def admin_headers():
    return {"Authorization": f"Bearer {ADMIN_TOKEN}"}


@pytest.fixture
def operator_a_headers():
    return {"Authorization": f"Bearer {OPERATOR_A_TOKEN}"}


@pytest.fixture
def operator_b_headers():
    return {"Authorization": f"Bearer {OPERATOR_B_TOKEN}"}

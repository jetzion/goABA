"""Test fixtures: a fresh SQLite file per test session and a seeded client."""

import os
import tempfile

TEST_DIR = tempfile.mkdtemp()
os.environ["TP_DATABASE_URL"] = f"sqlite:///{TEST_DIR}/test.db"
os.environ["TP_UPLOAD_DIR"] = f"{TEST_DIR}/uploads"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.seed import seed  # noqa: E402
from app.set_password import set_credentials  # noqa: E402

ADMIN_EMAIL = "dana@example.com"
ADMIN_PASSWORD = "dana test password"


@pytest.fixture(scope="session")
def client() -> TestClient:
    """HTTP client with tables created, a seeded client, signed in with a password as the Admin user."""
    with TestClient(app) as test_client:
        seed()
        with SessionLocal() as session:
            set_credentials(session, 1, ADMIN_EMAIL, ADMIN_PASSWORD)
        test_client.post("/api/v2/session/", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        yield test_client


@pytest.fixture
def plan_id(client: TestClient) -> int:
    """A new blank plan for each test."""
    response = client.post("/api/v2/treatment_plans/", json={"client_id": 1, "bay": "3"})
    return response.json()["id"]

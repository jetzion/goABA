"""Test fixtures: a fresh SQLite file per test session and a seeded client."""

import os
import tempfile

TEST_DIR = tempfile.mkdtemp()
os.environ["TP_DATABASE_URL"] = f"sqlite:///{TEST_DIR}/test.db"
os.environ["TP_UPLOAD_DIR"] = f"{TEST_DIR}/uploads"

import pyotp  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from app.models import AppUser  # noqa: E402
from app.seed import seed  # noqa: E402
from app.set_password import set_credentials  # noqa: E402

ADMIN_EMAIL = "dana@example.com"
ADMIN_PASSWORD = "dana test password"
ADMIN_MFA_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


@pytest.fixture(scope="session")
def client() -> TestClient:
    """HTTP client with tables created, a seeded client, signed in as the Admin user with a password and a code."""
    with TestClient(app) as test_client:
        seed()
        with SessionLocal() as session:
            set_credentials(session, 1, ADMIN_EMAIL, ADMIN_PASSWORD)
            admin = session.get_one(AppUser, 1)
            admin.mfa_secret, admin.mfa_enabled = ADMIN_MFA_SECRET, True
            session.commit()
        test_client.post("/api/v2/session/", json={"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD})
        test_client.post("/api/v2/session/mfa/", json={"code": pyotp.TOTP(ADMIN_MFA_SECRET).now()})
        yield test_client


@pytest.fixture
def plan_id(client: TestClient) -> int:
    """A new blank plan for each test."""
    response = client.post("/api/v2/treatment_plans/", json={"client_id": 1, "bay": "3"})
    return response.json()["id"]
